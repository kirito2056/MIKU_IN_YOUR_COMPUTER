"""채팅 API 요청/응답 스키마."""

from typing import Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    """채팅 요청 모델"""
    message: str
    max_new_tokens: Optional[int] = 200
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.9
    use_vision: bool = True  # Vision 실행 중일 때 시각 맥락 포함 여부


class ChatResponse(BaseModel):
    """채팅 응답 모델"""
    response: str
    model_loaded: bool
