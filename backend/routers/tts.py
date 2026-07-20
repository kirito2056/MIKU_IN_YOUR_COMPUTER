"""TTS 라우터 — GPT-SoVITS 합성/헬스체크."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from schemas.tts import TTSRequest
from services.tts_service import TTSServiceError

router = APIRouter(prefix="/api/tts", tags=["tts"])


@router.get("/health")
async def tts_health(request: Request):
    """GPT-SoVITS API 및 참조 음원 상태"""
    tts_service = request.app.state.tts_service
    if tts_service is None:
        return {"configured": False, "api_reachable": False, "ready": False}
    return tts_service.health_status()


@router.post("/synthesize")
async def tts_synthesize(request: Request, body: TTSRequest):
    """텍스트 → OGG 오디오 스트리밍 (GPT-SoVITS api.py 필요)"""
    tts_service = request.app.state.tts_service
    if tts_service is None or not tts_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="TTS가 설정되지 않았습니다. TTS_REF_WAV_PATH 또는 sliced.list 확인.",
        )

    try:
        def iter_audio():
            yield from tts_service.synthesize_stream(body.text)

        return StreamingResponse(iter_audio(), media_type="audio/ogg")
    except TTSServiceError as e:
        raise HTTPException(status_code=503, detail=str(e))
