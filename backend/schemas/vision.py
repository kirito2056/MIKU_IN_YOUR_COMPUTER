"""Vision 스키마 (docs/ai/vision_schema.md 기준).

Eye1(Webcam) 정량화 결과를 담는 Pydantic 모델. LLM에는 이 JSON이 아니라
summary/context_text 한 줄만 전달한다.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class FaceExpression(BaseModel):
    type: Literal["neutral", "happy", "sad", "angry", "surprised", "tired"]
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: List[float] = Field(min_length=4, max_length=4)  # [x, y, w, h] 정규화 좌표


class FacesInfo(BaseModel):
    count: int = Field(ge=0, le=10)
    detected: bool
    recognized_user: Optional[bool] = None  # None: 얼굴 인식(등록) 미구현
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    expressions: List[FaceExpression] = []


class GestureInfo(BaseModel):
    type: Literal[
        "none", "wave", "nod", "shake_head", "screen_cover", "thumbs_up", "point"
    ]
    confidence: float = Field(ge=0.0, le=1.0)
    hand_count: int = Field(ge=0, le=2)


class PostureInfo(BaseModel):
    type: Literal[
        "normal", "forward_head", "slouching", "leaning_left", "leaning_right"
    ]
    head_angle: Optional[float] = None  # 고개 pitch(도). 정면=0, 아래 볼수록 음수
    shoulder_alignment: Optional[float] = None  # 어깨선 기울기(도)
    confidence: float = Field(ge=0.0, le=1.0)


class EnvironmentInfo(BaseModel):
    light: Literal["bright", "normal", "dark", "very_dark"]
    light_level: float = Field(ge=0.0, le=1.0)
    motion: bool
    background_change: bool = False


class EventsInfo(BaseModel):
    ghost: bool = False
    multiple_faces: bool = False
    face_disappeared: bool = False
    face_appeared: bool = False


class Eye1Schema(BaseModel):
    source: Literal["webcam"] = "webcam"
    timestamp: float
    frame_id: int
    faces: FacesInfo
    gesture: GestureInfo
    posture: PostureInfo
    environment: EnvironmentInfo
    events: EventsInfo
    summary: str


# ------------------------------------------------------------- API 응답 모델


class CameraProbe(BaseModel):
    """probe_cameras() 결과 한 건 (카메라 후보)."""
    index: int
    width: int
    height: int
    brightness: float = Field(ge=0.0, le=1.0)
    thumbnail_b64: Optional[str] = None


class VisionRunStatus(BaseModel):
    """start/stop 응답: 캡처 스레드 실행 여부."""
    running: bool
    camera_index: Optional[int] = None


class VisionCamerasResponse(BaseModel):
    cameras: List[CameraProbe]
    was_running: bool
    current_index: int


class VisionStateResponse(BaseModel):
    running: bool
    error: Optional[str] = None
    context_text: Optional[str] = None  # LLM 프롬프트에 들어갈 '[시각] ...' 한 줄
    eye1: Optional[Eye1Schema] = None


def generate_eye1_summary(eye1: "Eye1Schema") -> str:
    """Eye1 정량화 결과 → 한국어 한 줄 요약 (LLM 프롬프트용)."""
    parts = []

    if eye1.faces.detected:
        if eye1.faces.recognized_user is True:
            parts.append(f"주인 {eye1.faces.count}명")
        elif eye1.faces.recognized_user is False:
            parts.append(f"낯선 사람 {eye1.faces.count}명")
        else:
            parts.append(f"얼굴 {eye1.faces.count}개 감지")
        expr_map = {
            "happy": "밝은 표정",
            "sad": "우울한 표정",
            "angry": "찌푸린 표정",
            "surprised": "놀란 표정",
            "tired": "피곤한 표정",
        }
        if eye1.faces.expressions:
            label = expr_map.get(eye1.faces.expressions[0].type)
            if label:
                parts.append(label)
    else:
        parts.append("얼굴 없음")

    gesture_map = {
        "wave": "손 흔들기",
        "nod": "고개 끄덕임",
        "shake_head": "고개 흔들기",
        "screen_cover": "화면 가리기",
        "thumbs_up": "엄지척",
        "point": "손가락 가리키기",
    }
    if eye1.gesture.type != "none":
        parts.append(gesture_map.get(eye1.gesture.type, eye1.gesture.type))

    posture_map = {
        "forward_head": "거북목",
        "slouching": "구부정한 자세",
        "leaning_left": "왼쪽으로 기울임",
        "leaning_right": "오른쪽으로 기울임",
    }
    if eye1.posture.type != "normal":
        parts.append(posture_map.get(eye1.posture.type, eye1.posture.type))

    if eye1.environment.light in ("dark", "very_dark"):
        parts.append("어두운 환경")

    if eye1.events.ghost:
        parts.append("유령 감지")
    if eye1.events.multiple_faces:
        parts.append("여러 얼굴 감지")
    if eye1.events.face_appeared:
        parts.append("방금 자리로 돌아옴")
    if eye1.events.face_disappeared:
        parts.append("방금 자리를 비움")

    return ", ".join(parts) if parts else "정상 상태"
