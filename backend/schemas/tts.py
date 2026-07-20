"""TTS API 요청 스키마."""

from pydantic import BaseModel, Field


class TTSRequest(BaseModel):
    """TTS 합성 요청"""
    text: str = Field(..., min_length=1)
