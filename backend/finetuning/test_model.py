"""
파인튜닝된 모델 테스트 스크립트
LoRA 어댑터를 로드하여 추론 테스트를 수행합니다.
"""
import torch
import os
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import argparse

def load_model_and_tokenizer(
    base_model_name: str,
    lora_path: str,
    use_4bit: bool = True
):
    """모델과 토크나이저 로드"""
    from transformers import BitsAndBytesConfig
    
    # 모델 경로 처리 (상대 경로인 경우 절대 경로로 변환)
    model_path = base_model_name
    if not os.path.isabs(model_path) and not model_path.startswith("google/") and not model_path.startswith("microsoft/"):
        # 상대 경로인 경우 backend 디렉토리 기준으로 변환
        backend_dir = Path(__file__).parent.parent
        model_path = str(backend_dir / model_path)
    
    print(f"📥 베이스 모델 로딩: {base_model_name} (경로: {model_path})")
    
    # GPU 사용 가능 여부 확인
    has_gpu = torch.cuda.is_available()
    if not has_gpu:
        print("⚠️  GPU를 찾을 수 없습니다. CPU 모드로 실행됩니다.")
        use_4bit = False  # CPU에서는 4-bit 양자화 사용 불가
    
    # 양자화 설정
    bnb_config = None
    device_map = "auto"
    
    if use_4bit and has_gpu:
        # GPU VRAM 확인 (32GB 이상이면 CPU 오프로드 불필요)
        gpu_vram_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3 if has_gpu else 0
        use_cpu_offload = False  # 버그 유발 방지
        
        try:
            # 추론을 위한 더 가볍고 안정적인 양자화 설정 (compute_dtype 제한)
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=False, # Double quant 끄기 (속도/안정성 향상)
                llm_int8_enable_fp32_cpu_offload=False,
            )
            if use_cpu_offload:
                print(f"   ⚠️  GPU VRAM이 {gpu_vram_gb:.1f}GB로 제한적입니다. CPU 오프로드 활성화.")
            else:
                print(f"   ✅ GPU VRAM: {gpu_vram_gb:.1f}GB - CPU 오프로드 없이 실행합니다.")
        except Exception as e:
            print(f"⚠️  4-bit 양자화 설정 실패: {e}")
            
    # 베이스 모델 로드
    try:
        # CPU 모드에서는 메모리 효율적인 로딩 사용
        load_kwargs = {
            "trust_remote_code": True,
        }
        
        if has_gpu:
            load_kwargs["torch_dtype"] = torch.float16
            load_kwargs["device_map"] = device_map
            # CUDA 커널 충돌 방지를 위해 SDPA 강제 활성화 (Gemma 3 이슈 우회)
            load_kwargs["attn_implementation"] = "sdpa"
            
            if bnb_config:
                load_kwargs["quantization_config"] = bnb_config
        else:
            # CPU 모드: 메모리 효율적인 로딩
            load_kwargs["torch_dtype"] = torch.float32
            load_kwargs["device_map"] = "cpu"
            load_kwargs["low_cpu_mem_usage"] = True
            # 디스크 오프로드 폴더 설정 (선택사항)
            import tempfile
            offload_folder = os.path.join(tempfile.gettempdir(), "model_offload")
            os.makedirs(offload_folder, exist_ok=True)
            load_kwargs["offload_folder"] = offload_folder
            print(f"💾 디스크 오프로드 폴더: {offload_folder}")
        
        base_model = AutoModelForCausalLM.from_pretrained(
            model_path,
            **load_kwargs
        )
    except (ValueError, RuntimeError, MemoryError) as e:
        error_msg = str(e)
        if "CPU or the disk" in error_msg and use_4bit and has_gpu:
            print("⚠️  GPU 메모리 부족으로 CPU 오프로드 모드로 전환합니다.")
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                llm_int8_enable_fp32_cpu_offload=True,
            )
            device_map = {"": 0 if has_gpu else "cpu"}
            base_model = AutoModelForCausalLM.from_pretrained(
                model_path,
                quantization_config=bnb_config,
                device_map=device_map,
                trust_remote_code=True,
            )
        elif "out of memory" in error_msg.lower() or "killed" in error_msg.lower() or isinstance(e, MemoryError):
            print("\n❌ 메모리 부족 오류 발생!")
            print("\n💡 해결 방법:")
            print("   1. 더 작은 모델 사용 (예: google/gemma-2-2b-it)")
            print("   2. GPU가 있는 환경에서 실행")
            print("   3. 모델을 양자화하여 사용")
            print("   4. 시스템 RAM을 늘리거나 스왑 공간 확보")
            raise RuntimeError(
                "모델이 너무 커서 현재 시스템 메모리로 로드할 수 없습니다. "
                "더 작은 모델을 사용하거나 GPU가 있는 환경에서 실행하세요."
            )
        else:
            raise
    
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # LoRA 어댑터 로드 (있는 경우)
    if lora_path:
        lora_full_path = lora_path
        if not os.path.isabs(lora_full_path):
            backend_dir = Path(__file__).parent.parent
            lora_full_path = str(backend_dir / lora_full_path)
        
        if os.path.exists(lora_full_path):
            print(f"📥 LoRA 어댑터 로딩: {lora_full_path}")
            model = PeftModel.from_pretrained(base_model, lora_full_path)
        else:
            print(f"⚠️  LoRA 경로를 찾을 수 없습니다: {lora_full_path}")
            print("   베이스 모델만 사용합니다.")
            model = base_model
    else:
        print("   베이스 모델만 사용합니다 (LoRA 없음)")
        model = base_model
    
    return model, tokenizer

def generate_response(
    model,
    tokenizer,
    user_message: str,
    max_new_tokens: int = 512,  # RTX 5080 16GB에 맞게 기본값 증가 (안전한 범위)
    temperature: float = 0.7,
    top_p: float = 0.9
):
    """응답 생성"""
    # Chat 템플릿 적용
    messages = [{"role": "user", "content": user_message}]
    input_text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )
    
    # 토크나이징
    inputs = tokenizer(input_text, return_tensors="pt")
    
    # Gemma 3 오류 방지를 위한 token_type_ids 추가
    if "token_type_ids" not in inputs:
        inputs["token_type_ids"] = torch.zeros_like(inputs["input_ids"])
    # 모델의 디바이스로 이동
    if hasattr(model, 'device'):
        inputs = inputs.to(model.device)
    elif hasattr(model, 'hf_device_map'):
        # device_map이 사용된 경우 첫 번째 디바이스 사용
        device = next(iter(model.hf_device_map.values())) if model.hf_device_map else "cpu"
        inputs = inputs.to(device)
    elif torch.cuda.is_available():
        inputs = inputs.to("cuda")
    else:
        inputs = inputs.to("cpu")
    
    # 생성
    with torch.no_grad():
        try:
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id
            )
        except RuntimeError as e:
                if "TensorCompare.cu" in str(e):
                    print("\n[내부 경고] Gemma 3 커널 충돌 감지됨. 안전 모드로 재시도합니다...")
                    # 안전 모드: token_type_ids 제거 후 재시도
                    if "token_type_ids" in inputs:
                        del inputs["token_type_ids"]
                    outputs = model.generate(
                        **inputs,
                        max_new_tokens=max_new_tokens,
                        temperature=temperature,
                        top_p=top_p,
                        do_sample=True,
                        pad_token_id=tokenizer.eos_token_id
                    )
                else:
                    raise
    
    # 디코딩
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # 응답 부분만 추출
    if "assistant" in response.lower():
        response = response.split("assistant")[-1].strip()
    
    return response

def test_personality(model, tokenizer):
    """성격 테스트 케이스 실행"""
    test_cases = [
        "너는 누구야?",
        "나를 뭐라고 불러야 해?",
        "다른 미쿠들은?",
        "비싼 거 사려고 해",
        "술 마셨어",
        "잘 자",
        "안녕",
    ]
    
    print("\n" + "="*60)
    print("🧪 성격 테스트 시작")
    print("="*60 + "\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"[테스트 {i}/{len(test_cases)}]")
        print(f"👤 사용자: {test_case}")
        print(f"🤖 미쿠: ", end="", flush=True)
        
        response = generate_response(model, tokenizer, test_case)
        print(response)
        print()

def interactive_chat(model, tokenizer):
    """대화형 채팅 모드"""
    print("\n" + "="*60)
    print("💬 대화형 모드 (종료: 'quit' 또는 'exit')")
    print("="*60 + "\n")
    
    while True:
        try:
            user_input = input("👤 당신: ").strip()
            
            if user_input.lower() in ["quit", "exit", "종료"]:
                print("\n👋 대화를 종료합니다.")
                break
            
            if not user_input:
                continue
            
            print("🤖 미쿠: ", end="", flush=True)
            response = generate_response(model, tokenizer, user_input)
            print(response)
            print()
            
        except KeyboardInterrupt:
            print("\n\n👋 대화를 종료합니다.")
            break
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")
            print()

def main():
    parser = argparse.ArgumentParser(description="파인튜닝된 모델 테스트")
    parser.add_argument(
        "--base_model", 
        type=str, 
        default="models/Gemma_12B",
        help="베이스 모델 경로 (기본값: models/Gemma_12B, backend/models/Gemma_12B 폴더 사용)"
    )
    parser.add_argument(
        "--lora_path",
        type=str,
        default="outputs/miku_lora",
        help="LoRA 어댑터 경로 (없으면 베이스 모델만 사용)"
    )
    parser.add_argument(
        "--no_lora",
        action="store_true",
        help="LoRA 어댑터 사용 안 함"
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["test", "chat"],
        default="test",
        help="실행 모드: test (성격 테스트) 또는 chat (대화형)"
    )
    parser.add_argument(
        "--use_4bit",
        action="store_true",
        default=True,
        help="4-bit 양자화 사용 (GPU가 없으면 자동으로 비활성화)"
    )
    parser.add_argument(
        "--no_4bit",
        action="store_false",
        dest="use_4bit",
        help="4-bit 양자화 비활성화 (CPU 모드에서 유용)"
    )
    
    args = parser.parse_args()
    
    print("🚀 파인튜닝된 모델 테스트 시작!")
    print(f"   베이스 모델: {args.base_model}")
    print(f"   LoRA 경로: {args.lora_path}")
    print(f"   모드: {args.mode}")
    
    # LoRA 경로 처리
    lora_path = None if args.no_lora else args.lora_path
    
    # 모델 로드
    model, tokenizer = load_model_and_tokenizer(
        args.base_model,
        lora_path,
        use_4bit=args.use_4bit
    )
    
    print("\n✅ 모델 로딩 완료!\n")
    
    # 모드에 따라 실행
    if args.mode == "test":
        test_personality(model, tokenizer)
    elif args.mode == "chat":
        interactive_chat(model, tokenizer)

if __name__ == "__main__":
    main()
