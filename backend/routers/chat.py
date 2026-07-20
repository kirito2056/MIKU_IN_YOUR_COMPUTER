"""채팅 라우터 — REST(/api/chat) + WebSocket(/ws/chat) 스트리밍."""

import asyncio
import base64
from threading import Thread

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)

from schemas.chat import ChatRequest, ChatResponse
from services.tts_service import TTSServiceError
from services.vision_service import get_vision_service

router = APIRouter(tags=["chat"])

TTS_WS_CHUNK_BYTES = 48 * 1024


def _with_vision_context(user_message: str) -> str:
    """Vision(Eye1)이 켜져 있고 상태가 신선하면 '[시각] ...' 맥락을 앞에 붙인다."""
    ctx = get_vision_service().get_context_text()
    if ctx is None:
        return user_message
    return f"현재 시각 맥락: {ctx}\n\n{user_message}"


def get_loaded_llm(request: Request):
    """로드 완료된 LLM 서비스를 반환. 미로드면 503."""
    llm_service = request.app.state.llm_service
    if llm_service is None or not llm_service._is_loaded:
        raise HTTPException(
            status_code=503,
            detail="모델이 로드되지 않았습니다. 서버 로그를 확인하세요."
        )
    return llm_service


@router.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, llm_service=Depends(get_loaded_llm)):
    """REST API 채팅 엔드포인트"""
    try:
        message = _with_vision_context(request.message) if request.use_vision else request.message
        response = llm_service.chat(
            message,
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


async def _stream_tts_over_ws(websocket: WebSocket, text: str) -> None:
    """LLM 응답 텍스트를 TTS로 합성해 WebSocket으로 base64 청크 전송."""
    tts_service = websocket.app.state.tts_service
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
    llm_service,
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


@router.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 채팅 엔드포인트"""
    await websocket.accept()

    llm_service = websocket.app.state.llm_service
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
                    if data.get("use_vision", True):
                        user_message = _with_vision_context(user_message)

                    if use_stream:
                        response = await _stream_llm_over_ws(
                            websocket,
                            llm_service,
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
