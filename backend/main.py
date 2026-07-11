from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional
import asyncio
import base64
import sys
import os
from threading import Thread
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 서비스 임포트
from services.llm_service import get_llm_service, LLMService
from services.llamacpp_service import get_llamacpp_service
from services.tts_service import get_tts_service, TTSService, TTSServiceError

app = FastAPI(title="MIKU IN YOUR COMPUTER (Backend)")

# CORS 설정 (Frontend 접속 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 배포 시에는 구체적인 출처로 제한 권장
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 서비스 인스턴스
llm_service: Optional[LLMService] = None
tts_service: Optional[TTSService] = None

TTS_WS_CHUNK_BYTES = 48 * 1024


@app.on_event("startup")
async def startup_event():
    """서버 시작 시 모델 로드"""
    global llm_service, tts_service
    tts_service = get_tts_service()
    tts_status = tts_service.health_status()
    if tts_status["ready"]:
        print(f"✅ TTS 서비스 준비 완료 ({tts_service.base_url})")
    elif tts_status["configured"]:
        print(f"⚠️  TTS 참조 음원 OK, API 미연결 ({tts_service.base_url})")
    else:
        print("⚠️  TTS 참조 음원 미설정 (음성 합성 비활성)")

    try:
        # llamacpp(기본): llama-server + GGUF / transformers: HF 4-bit 로드
        llm_backend = os.getenv("LLM_BACKEND", "llamacpp").lower()

        if llm_backend == "llamacpp":
            print("🚀 LLM 서비스 초기화 중... (llama.cpp)")
            llm_service = get_llamacpp_service()
        else:
            model_path = os.getenv("LLM_MODEL_PATH", "models/Gemma4_12B")
            lora_path = os.getenv("LORA_PATH", "models/outputs/miku_gemma4_v4")
            use_4bit = os.getenv("USE_4BIT", "true").lower() == "true"

            print(f"🚀 LLM 서비스 초기화 중... (transformers)")
            print(f"   모델 경로: {model_path}")
            if lora_path:
                print(f"   LoRA 경로: {lora_path}")

            llm_service = get_llm_service(
                model_path=model_path,
                lora_path=lora_path,
                use_4bit=use_4bit
            )
        print("✅ LLM 서비스 준비 완료!")
    except Exception as e:
        print(f"⚠️  모델 로딩 실패: {e}")
        print("   API는 모델 없이 실행됩니다. /chat 엔드포인트는 사용할 수 없습니다.")


@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 모델 언로드"""
    global llm_service
    if llm_service is not None:
        llm_service.unload_model()
        llm_service = None


async def _stream_tts_over_ws(websocket: WebSocket, text: str) -> None:
    """LLM 응답 텍스트를 TTS로 합성해 WebSocket으로 base64 청크 전송."""
    if tts_service is None or not tts_service.is_configured():
        await websocket.send_json({
            "type": "tts_error",
            "message": "TTS가 설정되지 않았습니다.",
        })
        return

    try:
        audio = await asyncio.to_thread(tts_service.synthesize, text)
    except TTSServiceError as e:
        await websocket.send_json({"type": "tts_error", "message": str(e)})
        return

    if not audio:
        await websocket.send_json({
            "type": "tts_error",
            "message": "TTS 결과가 비어 있습니다.",
        })
        return

    await websocket.send_json({"type": "audio_start", "format": "ogg"})
    for i in range(0, len(audio), TTS_WS_CHUNK_BYTES):
        chunk = audio[i : i + TTS_WS_CHUNK_BYTES]
        await websocket.send_json({
            "type": "audio_chunk",
            "data": base64.b64encode(chunk).decode("ascii"),
        })
    await websocket.send_json({"type": "audio_end"})


async def _stream_llm_over_ws(
    websocket: WebSocket,
    user_message: str,
    *,
    max_new_tokens: int = 200,
    temperature: float = 0.7,
    top_p: float = 0.9,
) -> str:
    """LLM 토큰 스트리밍 후 전체 텍스트 반환."""
    await websocket.send_json({"type": "stream_start"})

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def producer() -> None:
        try:
            for chunk in llm_service.chat_stream(
                user_message,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
            ):
                loop.call_soon_threadsafe(queue.put_nowait, ("chunk", chunk))
            loop.call_soon_threadsafe(queue.put_nowait, ("done", None))
        except Exception as exc:
            loop.call_soon_threadsafe(queue.put_nowait, ("error", exc))

    Thread(target=producer, daemon=True).start()

    parts: list[str] = []
    while True:
        kind, payload = await queue.get()
        if kind == "chunk":
            parts.append(payload)
            await websocket.send_json({"type": "stream_chunk", "text": payload})
        elif kind == "done":
            break
        elif kind == "error":
            raise payload

    full_text = "".join(parts)
    await websocket.send_json({"type": "stream_end", "message": full_text})
    return full_text


@app.get("/")
async def root():
    tts_ready = tts_service is not None and tts_service.health_status()["ready"]
    return {
        "message": "Miku Backend is running!",
        "platform": sys.platform,
        "model_loaded": llm_service is not None and llm_service._is_loaded,
        "tts_ready": tts_ready,
    }


@app.get("/health")
async def health_check():
    tts_status = tts_service.health_status() if tts_service else {"ready": False}
    return {
        "status": "healthy",
        "model_loaded": llm_service is not None and llm_service._is_loaded,
        "tts": tts_status,
    }


class ChatRequest(BaseModel):
    """채팅 요청 모델"""
    message: str
    max_new_tokens: Optional[int] = 200
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.9


class ChatResponse(BaseModel):
    """채팅 응답 모델"""
    response: str
    model_loaded: bool


class TTSRequest(BaseModel):
    """TTS 합성 요청"""
    text: str = Field(..., min_length=1)


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """REST API 채팅 엔드포인트"""
    if llm_service is None or not llm_service._is_loaded:
        raise HTTPException(
            status_code=503,
            detail="모델이 로드되지 않았습니다. 서버 로그를 확인하세요."
        )

    try:
        response = llm_service.chat(
            request.message,
            max_new_tokens=request.max_new_tokens,
            temperature=request.temperature,
            top_p=request.top_p
        )
        return ChatResponse(
            response=response,
            model_loaded=True
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"응답 생성 실패: {str(e)}")


@app.get("/api/tts/health")
async def tts_health():
    """GPT-SoVITS API 및 참조 음원 상태"""
    if tts_service is None:
        return {"configured": False, "api_reachable": False, "ready": False}
    return tts_service.health_status()


@app.post("/api/tts/synthesize")
async def tts_synthesize(request: TTSRequest):
    """텍스트 → OGG 오디오 스트리밍 (GPT-SoVITS api.py 필요)"""
    if tts_service is None or not tts_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="TTS가 설정되지 않았습니다. TTS_REF_WAV_PATH 또는 sliced.list 확인.",
        )

    try:
        def iter_audio():
            yield from tts_service.synthesize_stream(request.text)

        return StreamingResponse(iter_audio(), media_type="audio/ogg")
    except TTSServiceError as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 채팅 엔드포인트"""
    await websocket.accept()

    if llm_service is None or not llm_service._is_loaded:
        await websocket.send_json({
            "type": "error",
            "message": "모델이 로드되지 않았습니다."
        })
        await websocket.close()
        return

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "chat":
                user_message = data.get("message", "")

                if not user_message:
                    await websocket.send_json({
                        "type": "error",
                        "message": "메시지가 비어있습니다."
                    })
                    continue

                try:
                    gen_kwargs = {
                        "max_new_tokens": data.get("max_new_tokens", 200),
                        "temperature": data.get("temperature", 0.7),
                        "top_p": data.get("top_p", 0.9),
                    }
                    use_stream = data.get("stream", True)

                    if use_stream:
                        response = await _stream_llm_over_ws(
                            websocket,
                            user_message,
                            **gen_kwargs,
                        )
                    else:
                        response = llm_service.chat(user_message, **gen_kwargs)
                        await websocket.send_json({
                            "type": "response",
                            "message": response,
                        })

                    if data.get("with_tts"):
                        await _stream_tts_over_ws(websocket, response)

                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"응답 생성 실패: {str(e)}"
                    })

            elif msg_type == "tts":
                text = data.get("text", "").strip()
                if not text:
                    await websocket.send_json({
                        "type": "error",
                        "message": "텍스트가 비어있습니다."
                    })
                    continue
                await _stream_tts_over_ws(websocket, text)

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        print("WebSocket 연결 종료")
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except Exception:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
