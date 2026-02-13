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
    DataCollatorForLanguageModeling,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from datasets import load_dataset
import argparse

@dataclass
class ModelArguments:
    """모델 관련 인자"""
    model_name_or_path: str = field(
        default="models",  # 로컬 모델 경로 (backend/models)
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
        default="datasets/miku_personality_chat.json",
        metadata={"help": "학습 데이터셋 경로"}
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

def load_and_prepare_dataset(
    dataset_path: str,
    tokenizer: AutoTokenizer,
    max_seq_length: int = 2048
):
    """데이터셋 로드 및 전처리"""
    # JSON 파일 로드
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    def format_prompt(example):
        """프롬프트 포맷팅"""
        if "messages" in example:
            # Chat 형식
            messages = example["messages"]
            text = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=False
            )
        else:
            # Alpaca 형식
            instruction = example.get("instruction", "")
            input_text = example.get("input", "")
            output = example.get("output", "")
            
            if input_text:
                prompt = f"### Instruction:\n{instruction}\n\n### Input:\n{input_text}\n\n### Response:\n{output}"
            else:
                prompt = f"### Instruction:\n{instruction}\n\n### Response:\n{output}"
            text = prompt
        
        return {"text": text}
    
    # 데이터셋 포맷팅
    formatted_data = [format_prompt(item) for item in data]
    
    def tokenize_function(examples):
        """토크나이징 함수"""
        return tokenizer(
            examples["text"],
            truncation=True,
            max_length=max_seq_length,
            padding=False,
            return_tensors=None
        )
    
    # HuggingFace Dataset 형식으로 변환
    from datasets import Dataset
    dataset = Dataset.from_list(formatted_data)
    tokenized_dataset = dataset.map(
        tokenize_function,
        batched=True,
        remove_columns=dataset.column_names
    )
    
    return tokenized_dataset

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
    parser.add_argument("--model_name", type=str, default="models")
    parser.add_argument("--dataset_path", type=str, default="datasets/miku_personality_chat.json")
    parser.add_argument("--output_dir", type=str, default="outputs/miku_lora")
    parser.add_argument("--num_epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=4)
    parser.add_argument("--learning_rate", type=float, default=2e-4)
    parser.add_argument("--lora_r", type=int, default=16)
    parser.add_argument("--lora_alpha", type=int, default=32)
    parser.add_argument("--max_seq_length", type=int, default=2048)
    parser.add_argument("--use_4bit", action="store_true", default=True, help="4-bit 양자화 사용 (기본: True, 27B 모델 권장)")
    parser.add_argument("--no_4bit", action="store_false", dest="use_4bit", help="4-bit 양자화 비활성화")
    
    args = parser.parse_args()
    
    # 모델 경로 처리 (상대 경로인 경우 절대 경로로 변환)
    model_path = args.model_name
    if not os.path.isabs(model_path) and not model_path.startswith("google/") and not model_path.startswith("microsoft/"):
        # 상대 경로인 경우 backend 디렉토리 기준으로 변환
        backend_dir = Path(__file__).parent.parent
        model_path = str(backend_dir / model_path)
    
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
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # GPU 사용 가능 여부 확인
    has_gpu = torch.cuda.is_available()
    if not has_gpu:
        print("⚠️  GPU를 찾을 수 없습니다. CPU 모드로 실행됩니다.")
        args.use_4bit = False  # CPU에서는 4-bit 양자화 사용 불가
    
    # 양자화 설정
    bnb_config = None
    if args.use_4bit and has_gpu:
        try:
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=False,
                llm_int8_enable_fp32_cpu_offload=True,  # CPU 오프로드 허용
            )
        except Exception as e:
            print(f"⚠️  4-bit 양자화 설정 실패: {e}")
            print("   CPU 오프로드 모드로 전환합니다.")
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=False,
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
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            quantization_config=bnb_config,
            device_map=device_map,
            trust_remote_code=True,
            torch_dtype=torch.float16 if has_gpu else torch.float32,
        )
    except ValueError as e:
        if "CPU or the disk" in str(e) and args.use_4bit:
            print("⚠️  GPU 메모리 부족으로 CPU 오프로드 모드로 전환합니다.")
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=False,
                llm_int8_enable_fp32_cpu_offload=True,
            )
            device_map = {"": 0 if has_gpu else "cpu"}
            model = AutoModelForCausalLM.from_pretrained(
                model_path,
                quantization_config=bnb_config,
                device_map=device_map,
                trust_remote_code=True,
            )
        else:
            raise
    
    # LoRA 설정
    print("🔧 LoRA 설정 중...")
    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj"]
    
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
        model = prepare_model_for_kbit_training(model)
    
    model = get_peft_model(model, lora_config)
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
    
    # 데이터 콜레이터
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
    )
    
    # 학습 인자 설정
    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.num_epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=4,
        learning_rate=args.learning_rate,
        fp16=True,
        logging_steps=10,
        save_steps=100,
        save_total_limit=3,
        optim="paged_adamw_8bit",
        lr_scheduler_type="cosine",
        warmup_steps=10,
        report_to="none",
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
    
    print(f"\n✅ 파인튜닝 완료! 모델이 {args.output_dir}에 저장되었습니다.")
    print("\n💡 다음 단계:")
    print(f"   1. LoRA 어댑터를 로드하여 추론 테스트")
    print(f"   2. 대화 로그를 추가하여 데이터셋 확장")
    print(f"   3. 필요시 추가 파인튜닝 수행")

if __name__ == "__main__":
    main()
