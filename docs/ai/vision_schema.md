# Vision 스키마 명세 (Vision Schema Specification)

## 1. 개요

Vision 시스템은 두 개의 입력 소스(Eye1: Webcam, Eye2: Screen)로부터 구조화된 데이터를 생성하고, 이를 자연어로 변환하여 LLM에 전달합니다.

## 2. 기본 스키마 구조

### 2.1. Eye1 (Webcam) 스키마

```python
{
    "source": "webcam",
    "timestamp": float,  # Unix timestamp (초 단위)
    "frame_id": int,     # 프레임 순서 번호
    
    # 얼굴 인식
    "faces": {
        "count": int,                    # 감지된 얼굴 수 (0~10)
        "detected": bool,                 # 얼굴 감지 여부
        "recognized_user": Optional[bool], # 주인 인식 여부 (None: 인식 불가, True: 주인, False: 낯선 사람)
        "confidence": Optional[float],    # 인식 신뢰도 (0.0~1.0)
        "expressions": List[Dict],        # 감지된 표정들
        # [
        #   {
        #     "type": "neutral" | "happy" | "sad" | "angry" | "surprised" | "tired",
        #     "confidence": float,
        #     "bbox": [x, y, width, height]  # 얼굴 위치 (정규화 좌표 0~1)
        #   }
        # ]
    },
    
    # 제스처 인식
    "gesture": {
        "type": "none" | "wave" | "nod" | "shake_head" | "screen_cover" | "thumbs_up" | "point",
        "confidence": float,              # 제스처 인식 신뢰도 (0.0~1.0)
        "hand_count": int,                # 감지된 손 개수 (0~2)
        "hand_positions": List[Dict],     # 손 위치 정보
        # [
        #   {
        #     "bbox": [x, y, width, height],
        #     "landmarks": List[List[float]]  # 손 랜드마크 좌표 (21개 포인트)
        #   }
        # ]
    },
    
    # 자세 분석
    "posture": {
        "type": "normal" | "forward_head" | "slouching" | "leaning_left" | "leaning_right",
        "head_angle": Optional[float],    # 고개 각도 (도 단위, 정면=0)
        "shoulder_alignment": Optional[float],  # 어깨 정렬 각도
        "confidence": float
    },
    
    # 환경 감지
    "environment": {
        "light": "bright" | "normal" | "dark" | "very_dark",  # 밝기 레벨
        "light_level": float,             # 밝기 수치 (0.0~1.0)
        "motion": bool,                   # 움직임 감지 여부
        "background_change": bool         # 배경 변화 감지 (침입자 등)
    },
    
    # 특수 이벤트
    "events": {
        "ghost": bool,                    # 허공 얼굴 오탐 (유령 감지)
        "multiple_faces": bool,           # 여러 얼굴 감지 (침입자 가능성)
        "face_disappeared": bool,         # 얼굴이 사라짐 (사용자 이탈)
        "face_appeared": bool             # 얼굴이 나타남 (사용자 복귀)
    },
    
    # 요약 (자연어)
    "summary": str  # 예: "주인 1명, 고개 끄덕임, 밝은 환경"
}
```

### 2.2. Eye2 (Screen) 스키마

```python
{
    "source": "screen",
    "timestamp": float,
    "frame_id": int,
    
    # 화면 타입 분류
    "scene": {
        "type": "ide" | "game" | "browser" | "video" | "image_viewer" | "terminal" | "unknown",
        "confidence": float,
        "subtype": Optional[str],        # 세부 타입 (예: "vscode", "pycharm", "chrome", "firefox")
    },
    
    # 활성 애플리케이션
    "application": {
        "name": Optional[str],           # 예: "VS Code", "Chrome", "Steam"
        "window_title": Optional[str],   # 창 제목
        "is_fullscreen": bool,
        "is_maximized": bool
    },
    
    # 브라우저 정보 (scene_type이 "browser"일 때)
    "browser": {
        "url": Optional[str],            # 현재 URL
        "domain": Optional[str],         # 도메인만 추출 (예: "youtube.com")
        "search_query": Optional[str],   # 검색어 (URL에서 추출)
        "page_title": Optional[str]      # 페이지 제목
    },
    
    # IDE/에디터 정보 (scene_type이 "ide"일 때)
    "editor": {
        "language": Optional[str],       # 예: "python", "javascript", "typescript"
        "file_name": Optional[str],      # 열려있는 파일명
        "has_errors": Optional[bool],    # 에러 표시 여부
        "line_count": Optional[int]      # 코드 라인 수 (대략적)
    },
    
    # 게임 정보 (scene_type이 "game"일 때)
    "game": {
        "title": Optional[str],         # 게임 제목 (OCR 또는 윈도우 제목에서 추출)
        "is_paused": Optional[bool],    # 일시정지 여부
        "has_ui": bool                   # UI 요소 감지 여부
    },
    
    # OCR 결과 (선택적)
    "text_content": {
        "detected_text": List[str],      # 감지된 텍스트 목록
        "dominant_text": Optional[str]   # 가장 큰 텍스트 (제목 등)
    },
    
    # 요약 (자연어)
    "summary": str  # 예: "VS Code에서 Python 코드 편집 중", "YouTube에서 비디오 시청 중"
}
```

### 2.3. 통합 Vision Context (LLM에 전달할 최종 형태)

```python
{
    "eye1": Eye1Schema,  # 위의 Eye1 스키마
    "eye2": Eye2Schema,  # 위의 Eye2 스키마
    "timestamp": float,
    
    # 자연어 요약 (LLM에 직접 삽입)
    "context_text": str  # 예: "[시각] 웹캠: 주인 1명, 고개 끄덕임. 화면: VS Code에서 Python 코드 편집 중."
}
```

## 3. Pydantic 모델 정의

실제 구현 시 사용할 Pydantic 모델:

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime

class FaceExpression(BaseModel):
    type: Literal["neutral", "happy", "sad", "angry", "surprised", "tired"]
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: List[float] = Field(min_length=4, max_length=4)  # [x, y, w, h]

class FacesInfo(BaseModel):
    count: int = Field(ge=0, le=10)
    detected: bool
    recognized_user: Optional[bool] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    expressions: List[FaceExpression] = []

class HandPosition(BaseModel):
    bbox: List[float]
    landmarks: List[List[float]]

class GestureInfo(BaseModel):
    type: Literal["none", "wave", "nod", "shake_head", "screen_cover", "thumbs_up", "point"]
    confidence: float = Field(ge=0.0, le=1.0)
    hand_count: int = Field(ge=0, le=2)
    hand_positions: List[HandPosition] = []

class PostureInfo(BaseModel):
    type: Literal["normal", "forward_head", "slouching", "leaning_left", "leaning_right"]
    head_angle: Optional[float] = None
    shoulder_alignment: Optional[float] = None
    confidence: float = Field(ge=0.0, le=1.0)

class EnvironmentInfo(BaseModel):
    light: Literal["bright", "normal", "dark", "very_dark"]
    light_level: float = Field(ge=0.0, le=1.0)
    motion: bool
    background_change: bool

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

class SceneInfo(BaseModel):
    type: Literal["ide", "game", "browser", "video", "image_viewer", "terminal", "unknown"]
    confidence: float = Field(ge=0.0, le=1.0)
    subtype: Optional[str] = None

class ApplicationInfo(BaseModel):
    name: Optional[str] = None
    window_title: Optional[str] = None
    is_fullscreen: bool = False
    is_maximized: bool = False

class BrowserInfo(BaseModel):
    url: Optional[str] = None
    domain: Optional[str] = None
    search_query: Optional[str] = None
    page_title: Optional[str] = None

class EditorInfo(BaseModel):
    language: Optional[str] = None
    file_name: Optional[str] = None
    has_errors: Optional[bool] = None
    line_count: Optional[int] = None

class GameInfo(BaseModel):
    title: Optional[str] = None
    is_paused: Optional[bool] = None
    has_ui: bool = False

class TextContentInfo(BaseModel):
    detected_text: List[str] = []
    dominant_text: Optional[str] = None

class Eye2Schema(BaseModel):
    source: Literal["screen"] = "screen"
    timestamp: float
    frame_id: int
    scene: SceneInfo
    application: ApplicationInfo
    browser: Optional[BrowserInfo] = None
    editor: Optional[EditorInfo] = None
    game: Optional[GameInfo] = None
    text_content: TextContentInfo = TextContentInfo()
    summary: str

class VisionContext(BaseModel):
    eye1: Eye1Schema
    eye2: Eye2Schema
    timestamp: float
    context_text: str
```

## 4. 자연어 요약 생성 규칙

### 4.1. Eye1 요약 생성

```python
def generate_eye1_summary(eye1: Eye1Schema) -> str:
    parts = []
    
    # 얼굴 정보
    if eye1.faces.detected:
        if eye1.faces.recognized_user is True:
            parts.append(f"주인 {eye1.faces.count}명")
        elif eye1.faces.recognized_user is False:
            parts.append(f"낯선 사람 {eye1.faces.count}명")
        else:
            parts.append(f"얼굴 {eye1.faces.count}개 감지")
    else:
        parts.append("얼굴 없음")
    
    # 제스처
    if eye1.gesture.type != "none":
        gesture_map = {
            "wave": "손 흔들기",
            "nod": "고개 끄덕임",
            "shake_head": "고개 흔들기",
            "screen_cover": "화면 가리기",
            "thumbs_up": "엄지척",
            "point": "손가락 가리키기"
        }
        parts.append(gesture_map.get(eye1.gesture.type, eye1.gesture.type))
    
    # 자세
    if eye1.posture.type != "normal":
        posture_map = {
            "forward_head": "거북목",
            "slouching": "구부정한 자세",
            "leaning_left": "왼쪽으로 기울임",
            "leaning_right": "오른쪽으로 기울임"
        }
        parts.append(posture_map.get(eye1.posture.type, eye1.posture.type))
    
    # 환경
    if eye1.environment.light == "dark" or eye1.environment.light == "very_dark":
        parts.append("어두운 환경")
    
    # 특수 이벤트
    if eye1.events.ghost:
        parts.append("유령 감지")
    if eye1.events.multiple_faces:
        parts.append("여러 얼굴 감지")
    
    return ", ".join(parts) if parts else "정상 상태"
```

### 4.2. Eye2 요약 생성

```python
def generate_eye2_summary(eye2: Eye2Schema) -> str:
    parts = []
    
    # 화면 타입
    scene_map = {
        "ide": "코드 에디터",
        "game": "게임",
        "browser": "브라우저",
        "video": "비디오",
        "image_viewer": "이미지 뷰어",
        "terminal": "터미널",
        "unknown": "알 수 없음"
    }
    scene_name = scene_map.get(eye2.scene.type, eye2.scene.type)
    
    # 세부 정보 추가
    if eye2.scene.type == "ide" and eye2.editor:
        if eye2.editor.language:
            parts.append(f"{scene_name}({eye2.editor.language})")
        if eye2.editor.file_name:
            parts.append(f"파일: {eye2.editor.file_name}")
    elif eye2.scene.type == "browser" and eye2.browser:
        if eye2.browser.domain:
            parts.append(f"{scene_name}({eye2.browser.domain})")
        if eye2.browser.search_query:
            parts.append(f"검색: {eye2.browser.search_query}")
    elif eye2.scene.type == "game" and eye2.game:
        if eye2.game.title:
            parts.append(f"{eye2.game.title} 플레이 중")
    else:
        parts.append(scene_name)
    
    return " | ".join(parts) if parts else scene_name
```

### 4.3. 최종 Context Text 생성

```python
def generate_context_text(eye1: Eye1Schema, eye2: Eye2Schema) -> str:
    eye1_summary = generate_eye1_summary(eye1)
    eye2_summary = generate_eye2_summary(eye2)
    
    return f"[시각] 웹캠: {eye1_summary}. 화면: {eye2_summary}."
```

## 5. Phase 1 구현 예시 (더미 데이터)

```python
def create_dummy_eye1() -> Eye1Schema:
    """Phase 1용 더미 Eye1 데이터 생성"""
    return Eye1Schema(
        source="webcam",
        timestamp=time.time(),
        frame_id=0,
        faces=FacesInfo(
            count=1,
            detected=True,
            recognized_user=True,
            confidence=0.95,
            expressions=[FaceExpression(type="neutral", confidence=0.8, bbox=[0.3, 0.2, 0.4, 0.5])]
        ),
        gesture=GestureInfo(type="none", confidence=0.0, hand_count=0, hand_positions=[]),
        posture=PostureInfo(type="normal", confidence=0.9),
        environment=EnvironmentInfo(light="normal", light_level=0.7, motion=False, background_change=False),
        events=EventsInfo(),
        summary="주인 1명, 정상 상태"
    )

def create_dummy_eye2() -> Eye2Schema:
    """Phase 1용 더미 Eye2 데이터 생성"""
    return Eye2Schema(
        source="screen",
        timestamp=time.time(),
        frame_id=0,
        scene=SceneInfo(type="ide", confidence=0.9, subtype="vscode"),
        application=ApplicationInfo(name="VS Code", window_title="main.py - MIKU_IN_YOUR_COMPUTER", is_maximized=True),
        editor=EditorInfo(language="python", file_name="main.py", has_errors=False, line_count=184),
        summary="코드 에디터(python) | 파일: main.py"
    )
```

## 6. LLM 프롬프트 삽입 예시

```python
def build_messages_with_vision(user_message: str, vision_context: VisionContext) -> List[Dict[str, str]]:
    """Vision 컨텍스트를 포함한 메시지 리스트 생성"""
    messages = [
        {
            "role": "system",
            "content": "너는 미쿠야. 사용자의 시각적 상황을 인식하고 자연스럽게 반응해."
        },
        {
            "role": "user",
            "content": f"{vision_context.context_text}\n\n{user_message}"
        }
    ]
    return messages
```

## 7. 확장 가능성

- **Phase 2**: 실제 YOLO/OpenCV로 얼굴, 제스처, 자세 감지
- **Phase 3**: 소형 VLM으로 화면 요약 자동 생성
- **추후**: 프라이버시 필터 (블러, Blind 제스처 처리)
