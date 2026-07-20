"""Vision(Eye1) 라우터 — 웹캠 캡처 제어, 상태 조회, 미리보기 스트림."""

import asyncio
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from schemas.vision import (
    VisionCamerasResponse,
    VisionRunStatus,
    VisionStateResponse,
)
from services.vision_service import (
    VisionServiceError,
    get_vision_service,
    probe_cameras,
)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

# 모니터 페이지는 /vision 루트 경로라 API 라우터와 분리
page_router = APIRouter(tags=["vision"])
router = APIRouter(prefix="/api/vision", tags=["vision"])


@page_router.get("/vision")
async def vision_monitor_page():
    """Eye1 실시간 모니터 페이지 (폴링 기반)"""
    return FileResponse(STATIC_DIR / "vision_monitor.html")


@router.post("/start", response_model=VisionRunStatus)
async def vision_start(camera_index: Optional[int] = None):
    """Eye1(웹캠) 캡처·분석 시작. camera_index로 카메라 지정/전환 가능"""
    service = get_vision_service()
    try:
        service.start(camera_index=camera_index)
    except VisionServiceError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return VisionRunStatus(running=service.is_running, camera_index=service.camera_index)


@router.post("/stop", response_model=VisionRunStatus)
async def vision_stop():
    """Eye1(웹캠) 캡처·분석 중지"""
    service = get_vision_service()
    service.stop()
    return VisionRunStatus(running=service.is_running, camera_index=service.camera_index)


@router.get("/cameras", response_model=VisionCamerasResponse)
async def vision_cameras():
    """카메라 후보 목록 (인덱스별 썸네일 포함). 실행 중이면 캡처를 멈추고 훑는다"""
    service = get_vision_service()
    was_running = service.is_running
    service.stop()  # 장치 점유 해제 후 프로브
    cameras = await asyncio.to_thread(probe_cameras)
    return VisionCamerasResponse(
        cameras=cameras,
        was_running=was_running,
        current_index=service.camera_index,
    )


@router.get("/preview")
async def vision_preview():
    """랜드마크 오버레이 웹캠 미리보기 (MJPEG 스트림)"""
    service = get_vision_service()
    if not service.is_running:
        raise HTTPException(status_code=503, detail="Vision이 실행 중이 아닙니다.")

    async def gen():
        last = None
        while service.is_running:
            jpeg = service.get_preview_jpeg()
            if jpeg is not None and jpeg is not last:  # 같은 프레임 재전송 방지
                last = jpeg
                yield (
                    b"--frame\r\nContent-Type: image/jpeg\r\n"
                    + f"Content-Length: {len(jpeg)}\r\n\r\n".encode()
                    + jpeg
                    + b"\r\n"
                )
            await asyncio.sleep(0.02)

    return StreamingResponse(
        gen(), media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.get("/state", response_model=VisionStateResponse)
async def vision_state():
    """최신 Eye1 정량화 결과 + LLM에 들어갈 시각 맥락 문장"""
    service = get_vision_service()
    return VisionStateResponse(
        running=service.is_running,
        error=service.last_error,
        context_text=service.get_context_text(),
        eye1=service.get_state(),
    )
