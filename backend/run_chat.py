#!/usr/bin/env python3
"""
간단한 대화형 채팅 스크립트
모델을 로드하고 대화형으로 채팅할 수 있습니다.
"""
import sys
from pathlib import Path

# services 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

from services.llm_service import LLMService
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

def main():
    print("=" * 60)
    print("🤖 미쿠 AI 채팅")
    print("=" * 60)
    print()
    
    # 설정 읽기
    model_path = os.getenv("LLM_MODEL_PATH", "models/Gemma_12B")
    lora_path = os.getenv("LORA_PATH", None)
    use_4bit = os.getenv("USE_4BIT", "true").lower() == "true"
    
    print(f"📥 모델 로딩 중...")
    print(f"   모델 경로: {model_path}")
    if lora_path:
        print(f"   LoRA 경로: {lora_path}")
    print()
    
    # LLM 서비스 생성 및 로드
    try:
        llm = LLMService(
            model_path=model_path,
            lora_path=lora_path,
            use_4bit=use_4bit
        )
        llm.load_model()
        print()
        print("✅ 모델 로딩 완료!")
        print()
        print("💬 대화를 시작하세요! (종료: 'quit', 'exit', 또는 Ctrl+C)")
        print("=" * 60)
        print()
        
        # 대화 루프
        while True:
            try:
                user_input = input("👤 당신: ").strip()
                
                if user_input.lower() in ["quit", "exit", "종료"]:
                    print("\n👋 대화를 종료합니다.")
                    break
                
                if not user_input:
                    continue
                
                print("🤖 미쿠: ", end="", flush=True)
                response = llm.chat(user_input)
                print(response)
                print()
                
            except KeyboardInterrupt:
                print("\n\n👋 대화를 종료합니다.")
                break
            except Exception as e:
                print(f"\n❌ 오류 발생: {e}")
                print()
        
        # 모델 언로드
        llm.unload_model()
        
    except Exception as e:
        print(f"\n❌ 모델 로딩 실패: {e}")
        print("\n💡 확인 사항:")
        print("   1. backend/models/Gemma_12B 폴더에 모델 파일이 있는지 확인")
        print("   2. requirements.txt의 패키지가 설치되어 있는지 확인")
        print("   3. GPU가 있다면 CUDA가 제대로 설치되어 있는지 확인")
        sys.exit(1)

if __name__ == "__main__":
    main()
