"""
파인튜닝된 모델 테스트 스크립트
LoRA 어댑터를 로드하여 추론 테스트를 수행합니다.
"""
import torch
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
    
    print(f"📥 베이스 모델 로딩: {base_model_name}")
    
    # 양자화 설정
    bnb_config = None
    if use_4bit:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
        )
    
    # 베이스 모델 로드
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )
    
    tokenizer = AutoTokenizer.from_pretrained(base_model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # LoRA 어댑터 로드
    print(f"📥 LoRA 어댑터 로딩: {lora_path}")
    model = PeftModel.from_pretrained(base_model, lora_path)
    
    return model, tokenizer

def generate_response(
    model,
    tokenizer,
    user_message: str,
    max_new_tokens: int = 200,
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
    inputs = tokenizer(input_text, return_tensors="pt").to(model.device)
    
    # 생성
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )
    
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
        default="google/gemma-2-2b-it",
        help="베이스 모델 이름"
    )
    parser.add_argument(
        "--lora_path",
        type=str,
        default="outputs/miku_lora",
        help="LoRA 어댑터 경로"
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
        help="4-bit 양자화 사용"
    )
    
    args = parser.parse_args()
    
    print("🚀 파인튜닝된 모델 테스트 시작!")
    print(f"   베이스 모델: {args.base_model}")
    print(f"   LoRA 경로: {args.lora_path}")
    print(f"   모드: {args.mode}")
    
    # 모델 로드
    model, tokenizer = load_model_and_tokenizer(
        args.base_model,
        args.lora_path,
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
