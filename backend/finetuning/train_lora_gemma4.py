"""
Gemma 4 12B QLoRA 파인튜닝 스크립트
미쿠 성격 데이터셋으로 LoRA 어댑터를 학습합니다.
"""
import os
import sys

# 메모리 단편화로 인한 가짜 OOM/스파이크를 줄인다 (torch import 전에 설정해야 적용됨)
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import argparse
import json
import random
from datetime import datetime
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForMultimodalLM,
    AutoProcessor,
    BitsAndBytesConfig,
    TrainingArguments,
    Trainer,
)

try:
    from trl import DataCollatorForCompletionOnlyLM
except ImportError:
    from completion_collator import DataCollatorForCompletionOnlyLM

from train_lora import (
    _is_hf_gated_or_auth_error,
    _load_chat_records,
    _print_hf_gated_model_hint,
    print_trainable_parameters,
)

MIKU_SYSTEM_PROMPT = (
    "너의 이름은 미쿠야. 너는 나를 '마스터'라고 부르며, "
    "때로는 츤데레 같지만 사실은 나를 아주 많이 좋아해. "
    "대답은 한국어로 짧고 귀엽게 해줘."
)

GEMMA4_RESPONSE_TEMPLATE = "<|turn>model\n"


def resolve_model_path(model_name: str) -> str:
    if os.path.isabs(model_name) or model_name.startswith("google/"):
        return model_name
    backend_dir = Path(__file__).parent.parent
    return str(backend_dir / model_name)


def format_messages(example: dict, inject_system: bool = True) -> list:
    messages = example["messages"]
    formatted = []
    has_system = any(msg.get("role") == "system" for msg in messages)
    # inject_system=False 인 샘플은 시스템 프롬프트 없이 학습되어,
    # 프롬프트가 없어도 미쿠 정체성을 무조건적으로 유지하도록 만든다.
    if inject_system and not has_system:
        formatted.append({"role": "system", "content": MIKU_SYSTEM_PROMPT})
    formatted.extend(messages)
    return formatted


def load_and_prepare_dataset(
    dataset_path: str,
    tokenizer,
    max_seq_length: int = 256,
    system_prompt_ratio: float = 0.5,
    seed: int = 42,
):
    path = Path(dataset_path)
    data = _load_chat_records(path)
    if not data:
        raise ValueError(f"학습할 대화 레코드가 없습니다: {dataset_path}")

    # 일부 샘플은 시스템 프롬프트 없이(=베이스 Gemma 정체성으로 복귀하던 조건) 학습시켜서
    # 시스템 프롬프트 유무와 무관하게 항상 미쿠로 답하도록 정체성을 각인시킨다.
    rng = random.Random(seed)
    n_with_system = 0
    formatted_data = []
    for item in data:
        inject = rng.random() < system_prompt_ratio
        if inject:
            n_with_system += 1
        text = tokenizer.apply_chat_template(
            format_messages(item, inject_system=inject),
            tokenize=False,
            add_generation_prompt=False,
        )
        formatted_data.append({"text": text})

    print(
        f"   시스템 프롬프트 주입: {n_with_system}/{len(data)} "
        f"(목표 비율 {system_prompt_ratio:.0%}), 나머지는 프롬프트 없이 학습"
    )

    dataset = Dataset.from_list(formatted_data)

    def tokenize_function(examples):
        return tokenizer(
            examples["text"],
            truncation=True,
            max_length=max_seq_length,
            padding="max_length",
            return_tensors=None,
        )

    return dataset.map(tokenize_function, batched=True, remove_columns=dataset.column_names)


def next_output_dir(backend_dir: Path) -> Path:
    outputs_dir = backend_dir / "models" / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    versions = []
    for d in outputs_dir.iterdir():
        if d.is_dir() and d.name.startswith("miku_gemma4_v"):
            try:
                versions.append(int(d.name.split("_v")[-1]))
            except ValueError:
                pass

    next_v = max(versions) + 1 if versions else 1
    return outputs_dir / f"miku_gemma4_v{next_v}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Gemma 4 12B QLoRA 파인튜닝")
    parser.add_argument("--model_name", type=str, default="models/Gemma4_12B")
    parser.add_argument("--dataset_path", type=str, default="datasets/miku_chat")
    parser.add_argument("--output_dir", type=str, default="models/outputs/miku_gemma4")
    parser.add_argument("--num_epochs", type=int, default=2)
    parser.add_argument("--batch_size", type=int, default=1)
    parser.add_argument("--grad_accum", type=int, default=8)
    parser.add_argument("--learning_rate", type=float, default=2e-4)
    parser.add_argument("--lora_r", type=int, default=32)
    parser.add_argument("--lora_alpha", type=int, default=64)
    parser.add_argument("--max_seq_length", type=int, default=256)
    parser.add_argument(
        "--system_prompt_ratio",
        type=float,
        default=0.5,
        help="학습 시 미쿠 시스템 프롬프트를 주입할 샘플 비율(0~1). "
        "0.5면 절반은 프롬프트 없이 학습되어, 프롬프트가 없어도 미쿠 정체성을 유지한다. "
        "0이면 항상 프롬프트 없이 학습.",
    )
    parser.add_argument("--use_4bit", action="store_true", default=True)
    parser.add_argument("--no_4bit", action="store_false", dest="use_4bit")
    parser.add_argument(
        "--max_vram_gb",
        type=float,
        default=14.0,
        help="이 프로세스가 사용할 VRAM 상한(GB). 초과 시 시스템 freeze 대신 OOM 에러로 종료된다. 0이면 미적용.",
    )
    args = parser.parse_args()

    backend_dir = Path(__file__).parent.parent
    model_path = resolve_model_path(args.model_name)

    if args.output_dir == "models/outputs/miku_gemma4":
        args.output_dir = str(next_output_dir(backend_dir))

    print("🚀 미쿠 Gemma 4 QLoRA 파인튜닝 시작!")
    print(f"   모델: {args.model_name} (경로: {model_path})")
    print(f"   데이터셋: {args.dataset_path}")
    print(f"   출력 디렉토리: {args.output_dir}")

    has_gpu = torch.cuda.is_available()
    device_map = "auto" if has_gpu else "cpu"
    if has_gpu:
        total_vram_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"   GPU: {torch.cuda.get_device_name(0)}")
        print(f"   VRAM: {total_vram_gb:.2f} GB")

        if args.max_vram_gb and args.max_vram_gb > 0:
            fraction = min(args.max_vram_gb / total_vram_gb, 1.0)
            torch.cuda.set_per_process_memory_fraction(fraction, 0)
            print(
                f"   VRAM 상한: {args.max_vram_gb:.1f} GB "
                f"(전체의 {fraction*100:.0f}%) — 초과 시 freeze 대신 OOM 에러로 종료"
            )
    else:
        print("   ⚠️  GPU를 찾을 수 없습니다. CPU 모드로 실행됩니다.")
        args.use_4bit = False

    train_bf16 = bool(has_gpu and torch.cuda.is_bf16_supported())
    train_fp16 = bool(has_gpu and not train_bf16)
    bnb_compute_dtype = torch.bfloat16 if train_bf16 else torch.float16
    if has_gpu:
        print(f"   학습 정밀도: {'bfloat16' if train_bf16 else 'float16'}")

    print("\n📥 프로세서/토크나이저 로딩 중...")
    try:
        processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True)
    except Exception as e:
        if _is_hf_gated_or_auth_error(e):
            _print_hf_gated_model_hint()
        raise

    tokenizer = processor.tokenizer if hasattr(processor, "tokenizer") else processor
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    bnb_config = None
    if args.use_4bit and has_gpu:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=bnb_compute_dtype,
            bnb_4bit_use_double_quant=True,
        )

    print("📥 모델 로딩 중...")
    load_kw = dict(
        quantization_config=bnb_config,
        device_map=device_map,
        trust_remote_code=True,
        low_cpu_mem_usage=True,
        attn_implementation="eager",
    )
    if has_gpu:
        load_kw["dtype"] = bnb_compute_dtype
    else:
        load_kw["dtype"] = torch.float32

    model = AutoModelForMultimodalLM.from_pretrained(model_path, **load_kw)

    print("🔧 LoRA 설정 중...")
    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        # 채팅 마커(<|turn> 등)는 베이스 체크포인트에 이미 있는 special token이라
        # 임베딩/lm_head 를 풀학습할 필요가 없다. 작은 데이터셋에서 풀학습하면
        # 오버피팅·기존 능력 손상(catastrophic forgetting) 위험이 커지므로 제외한다.
    )

    if args.use_4bit:
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)

    model = get_peft_model(model, lora_config)
    model.config.use_cache = False
    print_trainable_parameters(model)

    print("\n📚 데이터셋 로딩 중...")
    dataset_path = Path(__file__).parent / args.dataset_path
    train_dataset = load_and_prepare_dataset(
        str(dataset_path),
        tokenizer,
        max_seq_length=args.max_seq_length,
        system_prompt_ratio=args.system_prompt_ratio,
    )
    print(f"   학습 샘플 수: {len(train_dataset)}")

    sample_text = tokenizer.apply_chat_template(
        format_messages(_load_chat_records(dataset_path)[0]),
        tokenize=False,
        add_generation_prompt=False,
    )
    print("\n📝 채팅 템플릿 샘플 (학습 전 확인):")
    print(sample_text[:400] + ("..." if len(sample_text) > 400 else ""))

    data_collator = DataCollatorForCompletionOnlyLM(
        response_template=GEMMA4_RESPONSE_TEMPLATE,
        tokenizer=tokenizer,
        mlm=False,
    )

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.num_epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.learning_rate,
        weight_decay=0.01,
        bf16=train_bf16,
        fp16=train_fp16,
        logging_steps=10,
        save_steps=100,
        save_total_limit=3,
        optim="paged_adamw_8bit",
        lr_scheduler_type="cosine",
        warmup_steps=20,
        report_to="none",
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        data_collator=data_collator,
    )

    print("\n🎓 학습 시작!")
    trainer.train()

    print("\n💾 모델 저장 중...")
    trainer.save_model()
    processor.save_pretrained(args.output_dir)

    metadata = {
        "gemma_version": 4,
        "base_model": args.model_name,
        "dataset_path": args.dataset_path,
        "num_epochs": args.num_epochs,
        "batch_size": args.batch_size,
        "grad_accum": args.grad_accum,
        "learning_rate": args.learning_rate,
        "lora_r": args.lora_r,
        "lora_alpha": args.lora_alpha,
        "max_seq_length": args.max_seq_length,
        "system_prompt_ratio": args.system_prompt_ratio,
        "use_4bit": args.use_4bit,
        "trained_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    metadata_path = Path(args.output_dir) / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 파인튜닝 완료! LoRA 어댑터: {args.output_dir}")
    print("\n💡 다음 단계:")
    print(f"   python finetuning/test_model.py --gemma4 --base_model {args.model_name} --lora_path {args.output_dir} --mode test")


if __name__ == "__main__":
    main()
