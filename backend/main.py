"""MIKU IN YOUR COMPUTER 백엔드 엔트리포인트.

앱 생성·lifespan(모델 로드/언로드)·CORS만 담당하고,
엔드포인트는 routers/(chat·tts·vision)에 나눠져 있다.
"""

import os
import sys
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# 환경 변수 로드 (services import 전에 실행)
load_dotenv()

from services.llamacpp_service import get_llamacpp_service
from services.tts_service import get_tts_service
from services.vision_service import get_vision_service, VisionServiceError
from routers import chat, tts, vision


@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 시작 시 모델 로드, 종료 시 언로드."""
    tts_service = get_tts_service()
    app.state.tts_service = tts_service
    tts_status = tts_service.health_status()
    if tts_status["ready"]:
        print(f"✅ TTS 서비스 준비 완료 ({tts_service.base_url})")
    elif tts_status["configured"]:
        print(f"⚠️  TTS 참조 음원 OK, API 미연결 ({tts_service.base_url})")
    else:
        print("⚠️  TTS 참조 음원 미설정 (음성 합성 비활성)")

    app.state.llm_service = None
    try:
        # llamacpp(기본): llama-server + GGUF / transformers: HF 4-bit 로드
        llm_backend = os.getenv("LLM_BACKEND", "llamacpp").lower()

        if llm_backend == "llamacpp":
            print("🚀 LLM 서비스 초기화 중... (llama.cpp)")
            app.state.llm_service = get_llamacpp_service()
        else:
            # transformers 백엔드에서만 torch/transformers를 로드한다.
            # (llamacpp 기본 경로에서는 torch 미설치여도 서버가 뜬다.)
            from services.llm_service import get_llm_service

            model_path = os.getenv("LLM_MODEL_PATH", "models/Gemma4_12B")
            lora_path = os.getenv("LORA_PATH", "models/outputs/miku_gemma4_v4")
            use_4bit = os.getenv("USE_4BIT", "true").lower() == "true"

            print(f"🚀 LLM 서비스 초기화 중... (transformers)")
            print(f"   모델 경로: {model_path}")
            if lora_path:
                print(f"   LoRA 경로: {lora_path}")

            app.state.llm_service = get_llm_service(
                model_path=model_path,
                lora_path=lora_path,
                use_4bit=use_4bit
            )
        print("✅ LLM 서비스 준비 완료!")
    except Exception as e:
        print(f"⚠️  모델 로딩 실패: {e}")
        print("   API는 모델 없이 실행됩니다. /chat 엔드포인트는 사용할 수 없습니다.")

    if os.getenv("VISION_AUTOSTART", "false").lower() == "true":
        try:
            get_vision_service().start()
            print("✅ Vision(Eye1) 서비스 시작 (웹캠 캡처 중)")
        except VisionServiceError as e:
            print(f"⚠️  Vision 시작 실패: {e}")

    yield

    get_vision_service().stop()
    if app.state.llm_service is not None:
        app.state.llm_service.unload_model()
        app.state.llm_service = None


app = FastAPI(title="MIKU IN YOUR COMPUTER (Backend)", lifespan=lifespan)

# CORS 설정 (Frontend 접속 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 배포 시에는 구체적인 출처로 제한 권장
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(tts.router)
app.include_router(vision.router)
app.include_router(vision.page_router)


@app.get("/")
async def root(request: Request):
    llm_service = request.app.state.llm_service
    tts_service = request.app.state.tts_service
    tts_ready = tts_service is not None and tts_service.health_status()["ready"]
    return {
        "message": "Miku Backend is running!",
        "platform": sys.platform,
        "model_loaded": llm_service is not None and llm_service._is_loaded,
        "tts_ready": tts_ready,
    }


@app.get("/health")
async def health_check(request: Request):
    llm_service = request.app.state.llm_service
    tts_service = request.app.state.tts_service
    tts_status = tts_service.health_status() if tts_service else {"ready": False}
    return {
        "status": "healthy",
        "model_loaded": llm_service is not None and llm_service._is_loaded,
        "tts": tts_status,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
