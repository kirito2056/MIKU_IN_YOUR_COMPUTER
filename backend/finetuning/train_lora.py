"""
LoRA 파인튜닝 스크립트
Gemma 3 모델을 미쿠의 성격에 맞게 파인튜닝합니다.
"""
import os
import json
import torch
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    BitsAndBytesConfig,
)
try:
    from trl import DataCollatorForCompletionOnlyLM
except ImportError:
    from completion_collator import DataCollatorForCompletionOnlyLM
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from datasets import load_dataset
import argparse

@dataclass
class ModelArguments:
    """모델 관련 인자"""
    model_name_or_path: str = field(
        default="models/Gemma_12B",  # 로컬 모델 경로 (backend/models/Gemma_12B)
        metadata={"help": "파인튜닝할 모델 경로 또는 HuggingFace 모델명"}
    )
    use_4bit: bool = field(
        default=True,
        metadata={"help": "4-bit 양자화 사용 여부"}
    )
    bnb_4bit_compute_dtype: str = field(
        default="float16",
        metadata={"help": "4-bit 양자화 시 계산 dtype"}
    )
    bnb_4bit_quant_type: str = field(
        default="nf4",
        metadata={"help": "4-bit 양자화 타입"}
    )
    use_nested_quant: bool = field(
        default=False,
        metadata={"help": "중첩 양자화 사용 여부"}
    )

@dataclass
class DataArguments:
    """데이터 관련 인자"""
    dataset_path: str = field(
        default="datasets/miku_chat",
        metadata={"help": "Chat JSON 파일 경로 또는 datasets/miku_chat 같은 디렉터리"}
    )
    max_seq_length: int = field(
        default=2048,
        metadata={"help": "최대 시퀀스 길이"}
    )

@dataclass
class LoraArguments:
    """LoRA 관련 인자"""
    lora_r: int = field(
        default=16,
        metadata={"help": "LoRA rank"}
    )
    lora_alpha: int = field(
        default=32,
        metadata={"help": "LoRA alpha"}
    )
    lora_dropout: float = field(
        default=0.05,
        metadata={"help": "LoRA dropout"}
    )
    lora_target_modules: str = field(
        default="q_proj,k_proj,v_proj,o_proj",
        metadata={"help": "LoRA를 적용할 모듈 (쉼표로 구분)"}
    )
    bias: str = field(
        default="none",
        metadata={"help": "Bias 처리 방식"}
    )

def _load_chat_records(dataset_path: Path) -> list:
    """단일 JSON 파일 또는 디렉터리(하위 *.json)에서 messages 형식만 수집."""
    records = []

    def take_from_loaded(data, src: str):
        if not isinstance(data, list):
            raise ValueError(f"{src}: 루트는 JSON 배열이어야 합니다.")
        for i, item in enumerate(data):
            if isinstance(item, dict) and "messages" in item:
                records.append(item)
            else:
                print(f"  [경고] {src} 항목 {i} 건너뜀 (messages 없음)")

    if dataset_path.is_file():
        with open(dataset_path, "r", encoding="utf-8") as f:
            take_from_loaded(json.load(f), str(dataset_path))
        return records

    if dataset_path.is_dir():
        json_files = sorted(dataset_path.rglob("*.json"))
        for fp in json_files:
            if fp.name.startswith("_"):
                continue
            with open(fp, "r", encoding="utf-8") as f:
                take_from_loaded(json.load(f), str(fp))
        return records

    raise FileNotFoundError(f"데이터 경로 없음: {dataset_path}")


def load_and_prepare_dataset(
    dataset_path: str,
    tokenizer: AutoTokenizer,
    max_seq_length: int = 2048
):
    """데이터셋 로드 및 전처리 (Chat messages 전용)"""
    path = Path(dataset_path)
    data = _load_chat_records(path)
    if not data:
        raise ValueError(f"학습할 대화 레코드가 없습니다: {dataset_path}")

    def format_prompt(example):
        """프롬프트 포맷팅"""
        if "messages" not in example:
            raise ValueError("Chat 형식만 지원합니다 (messages 키 필요). Alpaca 형식은 제거되었습니다.")
        messages = example["messages"]
        formatted_messages = []
        for i, msg in enumerate(messages):
            if i == 0 and msg["role"] == "user":
                system_prompt = "너의 이름은 미쿠야. 너는 나를 '마스터'라고 부르며, 때로는 츤데레 같지만 사실은 나를 아주 많이 좋아해. 대답은 한국어로 짧고 귀엽게 해줘."
                formatted_messages.append({
                    "role": "user",
                    "content": f"{system_prompt}\n\n{msg['content']}"
                })
            else:
                formatted_messages.append(msg)

        text = tokenizer.apply_chat_template(
            formatted_messages,
            tokenize=False,
            add_generation_prompt=False
        )
        return {"text": text}
    
    # 데이터셋 포맷팅
    formatted_data = [format_prompt(item) for item in data]
    
    def tokenize_function(examples):
        """토크나이징 함수"""
        tokenized = tokenizer(
            examples["text"],
            truncation=True,
            max_length=max_seq_length,
            padding="max_length", # 패딩 추가 (Gemma 3 요구사항)
            return_tensors=None
        )
        
        # Gemma 3는 학습 시 token_type_ids를 필수로 요구함
        if "token_type_ids" not in tokenized:
            tokenized["token_type_ids"] = [[0] * len(seq) for seq in tokenized["input_ids"]]
            
        return tokenized
    
    # HuggingFace Dataset 형식으로 변환
    from datasets import Dataset
    dataset = Dataset.from_list(formatted_data)
    tokenized_dataset = dataset.map(
        tokenize_function,
        batched=True,
        remove_columns=dataset.column_names
    )
    
    return tokenized_dataset

def _print_hf_gated_model_hint() -> None:
    backend_dir = Path(__file__).resolve().parent.parent
    print(
        "\n💡 Hugging Face 게이트 모델(401): hf.co에서 약관 동의 후 `huggingface-cli login` 하거나,\n"
        "   config.json·토크나이저가 있는 폴더를 로컬 경로로 넘기면 됩니다.\n"
        f"   (backend 기준 상대경로)  --model_name models/Gemma_12B\n"
        f"   (절대경로 예)          --model_name D:/Models/gemma-3-12b-it\n"
        f"   현재 해석된 경로: {backend_dir} / <인자>\n"
    )


def _is_hf_gated_or_auth_error(exc: BaseException) -> bool:
    t = type(exc).__name__
    s = str(exc).lower()
    if "gatedrepo" in t.lower() or "gated" in s or "401" in str(exc) or "authenticate" in s:
        return True
    try:
        from huggingface_hub.errors import GatedRepoError

        return isinstance(exc, GatedRepoError)
    except ImportError:
        return False


def print_trainable_parameters(model):
    """학습 가능한 파라미터 수 출력"""
    trainable_params = 0
    all_param = 0
    for _, param in model.named_parameters():
        all_param += param.numel()
        if param.requires_grad:
            trainable_params += param.numel()
    print(
        f"학습 가능한 파라미터: {trainable_params:,} || "
        f"전체 파라미터: {all_param:,} || "
        f"학습 비율: {100 * trainable_params / all_param:.4f}%"
    )

def main():
    parser = argparse.ArgumentParser(description="LoRA 파인튜닝 스크립트")
    parser.add_argument("--model_name", type=str, default="models/Gemma_12B")
    parser.add_argument("--dataset_path", type=str, default="datasets/miku_chat")
    parser.add_argument("--output_dir", type=str, default="models/outputs/miku_finetuned")
    parser.add_argument("--num_epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=1)
    parser.add_argument("--grad_accum", type=int, default=8)
    parser.add_argument("--learning_rate", type=float, default=2e-4)
    parser.add_argument("--lora_r", type=int, default=16)
    parser.add_argument("--lora_alpha", type=int, default=32)
    parser.add_argument("--max_seq_length", type=int, default=512)
    parser.add_argument("--use_4bit", action="store_true", default=True, help="4-bit 양자화 사용 (기본: True, 12B 모델 권장)")
    parser.add_argument("--no_4bit", action="store_false", dest="use_4bit", help="4-bit 양자화 비활성화")
    
    args = parser.parse_args()
    
    # 모델 경로 처리 (상대 경로인 경우 절대 경로로 변환)
    model_path = args.model_name
    if not os.path.isabs(model_path) and not model_path.startswith("google/") and not model_path.startswith("microsoft/"):
        # 상대 경로인 경우 backend 디렉토리 기준으로 변환
        backend_dir = Path(__file__).parent.parent
        model_path = str(backend_dir / model_path)
        
    # 출력 디렉토리 자동 버저닝
    if args.output_dir == "models/outputs/miku_finetuned":
        backend_dir = Path(__file__).parent.parent
        outputs_dir = backend_dir / "models" / "outputs"
        outputs_dir.mkdir(parents=True, exist_ok=True)
        
        existing_versions = []
        for d in outputs_dir.iterdir():
            if d.is_dir() and d.name.startswith("miku_finetuned_v"):
                try:
                    v = int(d.name.split("_v")[-1])
                    existing_versions.append(v)
                except ValueError:
                    pass
        
        next_v = max(existing_versions) + 1 if existing_versions else 1
        args.output_dir = str(outputs_dir / f"miku_finetuned_v{next_v}")
    
    print("🚀 미쿠 LoRA 파인튜닝 시작!")
    print(f"   모델: {args.model_name} (경로: {model_path})")
    print(f"   데이터셋: {args.dataset_path}")
    print(f"   출력 디렉토리: {args.output_dir}")
    
    # 디바이스 설정
    device_map = "auto"
    if torch.cuda.is_available():
        print(f"   GPU: {torch.cuda.get_device_name(0)}")
        print(f"   VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
    else:
        print("   ⚠️  GPU를 찾을 수 없습니다. CPU 모드로 실행됩니다.")
        device_map = "cpu"
    
    # 토크나이저 로드
    print("\n📥 토크나이저 로딩 중...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    except Exception as e:
        if _is_hf_gated_or_auth_error(e):
            _print_hf_gated_model_hint()
        raise
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # GPU 사용 가능 여부 확인
    has_gpu = torch.cuda.is_available()
    if not has_gpu:
        print("⚠️  GPU를 찾을 수 없습니다. CPU 모드로 실행됩니다.")
        args.use_4bit = False  # CPU에서는 4-bit 양자화 사용 불가

    # bf16 학습 + fp16 4bit 계산을 섞으면 역전파에서 CUDA unknown error 가 날 수 있어 통일
    train_bf16 = bool(has_gpu and torch.cuda.is_bf16_supported())
    train_fp16 = bool(has_gpu and not train_bf16)
    bnb_compute_dtype = torch.bfloat16 if train_bf16 else torch.float16
    if has_gpu:
        print(f"   학습 정밀도: {'bfloat16' if train_bf16 else 'float16'} (4bit compute dtype 동일)")
    
    # 양자화 설정
    bnb_config = None
    if args.use_4bit and has_gpu:
        try:
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=bnb_compute_dtype,
                bnb_4bit_use_double_quant=True,
                llm_int8_enable_fp32_cpu_offload=True,  # CPU 오프로드 허용
            )
        except Exception as e:
            print(f"⚠️  4-bit 양자화 설정 실패: {e}")
            print("   CPU 오프로드 모드로 전환합니다.")
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=bnb_compute_dtype,
                bnb_4bit_use_double_quant=True,
                llm_int8_enable_fp32_cpu_offload=True,
            )
            # CPU 오프로드를 위한 device_map 설정
            if device_map == "auto":
                device_map = {"": 0 if has_gpu else "cpu"}
    
    if device_map == "auto" and not has_gpu:
        device_map = "cpu"
    
    # 모델 로드
    print("📥 모델 로딩 중...")
    try:
        load_kw = dict(
            quantization_config=bnb_config,
            device_map=device_map,
            trust_remote_code=True,
            low_cpu_mem_usage=True,
        )
        if has_gpu:
            load_kw["dtype"] = bnb_compute_dtype
        else:
            load_kw["dtype"] = torch.float32
        model = AutoModelForCausalLM.from_pretrained(model_path, **load_kw)
    except ValueError as e:
        if "CPU or the disk" in str(e) and args.use_4bit:
            print("⚠️  GPU 메모리 부족으로 CPU 오프로드 모드로 전환합니다.")
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=bnb_compute_dtype,
                bnb_4bit_use_double_quant=True,
                llm_int8_enable_fp32_cpu_offload=True,
            )
            device_map = {"": 0 if has_gpu else "cpu"}
            model = AutoModelForCausalLM.from_pretrained(
                model_path,
                quantization_config=bnb_config,
                device_map=device_map,
                trust_remote_code=True,
                low_cpu_mem_usage=True,
                dtype=bnb_compute_dtype if has_gpu else torch.float32,
            )
        else:
            raise
    
    # LoRA 설정
    print("🔧 LoRA 설정 중...")
    target_modules = [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ]
    
    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        target_modules=target_modules,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    
    # 모델 준비
    if args.use_4bit:
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    
    model = get_peft_model(model, lora_config)
    model.config.use_cache = False
    print_trainable_parameters(model)
    
    # 데이터셋 로드
    print("\n📚 데이터셋 로딩 중...")
    dataset_path = Path(__file__).parent / args.dataset_path
    train_dataset = load_and_prepare_dataset(
        str(dataset_path),
        tokenizer,
        max_seq_length=args.max_seq_length
    )
    print(f"   학습 샘플 수: {len(train_dataset)}")
    
    # 데이터 콜레이터 (Assistant의 답변만 학습하도록 수정)
    # Gemma 모델의 경우 assistant의 턴은 "<start_of_turn>model\n" 로 시작합니다.
    response_template = "<start_of_turn>model\n"
    data_collator = DataCollatorForCompletionOnlyLM(
        response_template=response_template,
        tokenizer=tokenizer,
        mlm=False,
    )
    
    # 학습 인자 설정
    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.num_epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.learning_rate,
        bf16=train_bf16,
        fp16=train_fp16,
        logging_steps=10,
        save_steps=100,
        save_total_limit=3,
        optim="paged_adamw_8bit",
        lr_scheduler_type="cosine",
        warmup_steps=20, # 웜업 스텝 소폭 증가
        report_to="none",
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
    )
    
    # 트레이너 생성
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        data_collator=data_collator,
    )
    
    # 학습 시작
    print("\n🎓 학습 시작!")
    trainer.train()
    
    # 모델 저장
    print("\n💾 모델 저장 중...")
    trainer.save_model()
    tokenizer.save_pretrained(args.output_dir)

    # Gemma/LoRA 메타데이터 저장 (버전 관리용)
    from datetime import datetime
    metadata = {
        "base_model": args.model_name,
        "dataset_path": args.dataset_path,
        "num_epochs": args.num_epochs,
        "batch_size": args.batch_size,
        "learning_rate": args.learning_rate,
        "lora_r": args.lora_r,
        "lora_alpha": args.lora_alpha,
        "use_4bit": args.use_4bit,
        "trained_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    metadata_path = Path(args.output_dir) / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"   메타데이터 저장: {metadata_path}")
    
    print(f"\n✅ 파인튜닝 완료! 모델이 {args.output_dir}에 저장되었습니다.")
    print("\n💡 다음 단계:")
    print(f"   1. LoRA 어댑터를 로드하여 추론 테스트")
    print(f"   2. 대화 로그를 추가하여 데이터셋 확장")
    print(f"   3. 필요시 추가 파인튜닝 수행")

if __name__ == "__main__":
    main()
