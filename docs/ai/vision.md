# 듀얼 비전 시스템 (Dual Vision System)

## 1. 구조
두 개의 '눈'을 통해 사용자와 환경을 인식합니다.

### Eye 1: Webcam (사용자 관찰)
-   **Face Recognition**: 주인(반가움) vs 낯선 사람(경계).
-   **Gesture**: 손 흔들기, 고개 끄덕임, 화면 가리기(Blind).
-   **Posture Check**: 거북목 감지 시 잔소리.
-   **Mimic Mode**: 거울 놀이 (표정 따라하기).
-   **Light Sensor**: 방 불 꺼짐 감지 -> 야광봉 모드.
-   **Ghost Check**: 허공에 얼굴 인식 시 공포 반응.

### Eye 2: Screen Capture (화면 인식)
-   **Game/IDE**: 게임 화면이나 코드 에디터 인식 -> 훈수.
-   **Browser URL**: 검색어 감지 -> 취향 훈수.

## 2. 프라이버시 필터 (추후 적용)
-   **Blur Logic**: 비밀번호, 카드번호 등 민감 정보 자동 블러 처리.
-   **Blind Gesture**: 손바닥으로 가리면 "안 볼게" 시전.

---

## 3. 구현 기획: Vision 전용 AI + 27B 연동

프라이버시는 추후 적용하고, **Vision만 처리하는 AI를 두 번째 GPU에 두고**, Eye1/Eye2 결과를 **정량화한 뒤 27B에 텍스트로 넣어** 자연스러운 응답을 만드는 흐름을 목표로 한다.

### 3.1. 역할 분리

| 장치 | 역할 | 비고 |
|------|------|------|
| **GPU 0 (RTX 5080)** | **27B LLM 전담** | Vision 부하 제거 → 추론 속도·안정성 확보 |
| **GPU 1 (RTX 3090)** | **Vision 전용 AI** | Eye1 + Eye2 프레임 수신 → 정량화(구조화) → 텍스트/JSON 출력 |

- 클라이언트는 기존처럼 `POST /api/vision/frame`으로 `webcam` / `screen` 프레임을 전송.
- Backend의 **Vision 서비스는 GPU 1에서만** 동작하며, 27B에는 **픽셀이 아닌 정량화 결과만** 전달한다.

### 3.2. 정량화(Structured Output) 정의

27B는 **이미지를 직접 보지 않고**, Vision AI가 뽑은 **구조화된 데이터를 텍스트로** 받는다. 그래야 토큰 효율이 좋고, “지금 화면에 뭐가 보인다”를 안정적으로 반영할 수 있다.

#### Eye1 (Webcam) 스키마 예시

```json
{
  "source": "webcam",
  "faces": { "count": 1, "recognized_user": true, "expression": "neutral" },
  "gesture": "none | wave | nod | screen_cover",
  "posture": "normal | forward_head",
  "light": "normal | dark",
  "ghost": false
}
```

- **faces**: 인원 수, 주인 여부, 표정(선택).
- **gesture**: 손 흔들기, 고개 끄덕임, 화면 가리기 등.
- **posture**: 거북목 등 자세 이슈.
- **light**: 방 밝기 → 야광봉 등 연출 트리거.
- **ghost**: 허공 얼굴 오탐 시 `true`.

#### Eye2 (Screen) 스키마 예시

```json
{
  "source": "screen",
  "scene_type": "ide | game | browser | unknown",
  "dominant_app": "VS Code | Chrome | ...",
  "url_bar": null,
  "summary_one_line": "에디터에서 Python 코드가 열려 있음."
}
```

- **scene_type**: 게임/IDE/브라우저 등.
- **summary_one_line**: (선택) 소형 VLM 또는 규칙으로 만든 **한 줄 설명** → 27B에 넣기 좋은 형태.

#### 27B에 넣을 최종 “시각 맥락” 텍스트

정량화 JSON을 그대로 넣기보다, **짧은 자연어 문장 1~2줄**로 합치면 27B가 더 잘 처리한다.

- 예:  
  `[시각] 웹캠: 주인 1명, 고개 끄덕임. 화면: VS Code에서 Python 코드 편집 중.`

- 시스템 프롬프트 또는 매 턴 유저 메시지 직전에  
  `현재 시각 맥락: ...`  
  형태로 삽입.

### 3.3. 데이터 흐름 (전체)

1. **클라이언트**: 웹캠·화면 캡처를 1~5 fps로 `POST /api/vision/frame` 전송 (`source`: `webcam` | `screen`).
2. **Backend (Vision 서비스, GPU 1)**:
   - 수신한 프레임으로 Vision 전용 모델 추론 (객체/얼굴/제스처/OCR 또는 소형 VLM 등).
   - Eye1/Eye2 각각에 대해 위 스키마대로 **정량화 JSON** 생성.
   - (선택) JSON → **한 줄 요약 문장** 생성 후 RAM/캐시에 유지.
3. **Backend (LLM 호출 시)**:
   - 대화 컨텍스트 구성 시, 최신 “시각 맥락” 문장을 포함해 프롬프트 구성.
   - **GPU 0**의 27B만 호출 (이미지 없음, 텍스트만).
4. **27B**: “현재 시각 맥락: …”을 읽고 상황에 맞는 자연스러운 답변 생성.

### 3.4. Vision AI on GPU 1 후보

- **객체/얼굴/제스처**: YOLO(v8 등) + OpenCV 또는 경량 규칙 (손 영역, 고개 각도 등).
- **화면 한 줄 요약**:  
  - 규칙 + OCR(예: Tesseract, EasyOCR)로 “에디터/게임/URL”만 구분하거나,  
  - **소형 VLM**(Phi-3 Vision, Qwen2-VL-2B, LLaVA 등)으로 “한 문장 설명” 생성 후 27B에 전달.
- 27B는 **텍스트만** 입력받으므로, Vision 모델은 전부 GPU 1에 두면 된다.

### 3.5. 구현 단계 제안

| 단계 | 내용 |
|------|------|
| **Phase 1** | Eye1/Eye2 **정량화 스키마 확정** + 더미 JSON으로 27B 프롬프트에 “시각 맥락” 삽입 테스트. (Vision 모델 없이도 연동 검증) |
| **Phase 2** | GPU 1에 **YOLO + 경량 로직** 올려서 웹캠 얼굴/제스처/자세, 화면은 scene_type 정도만 실제 정량화. |
| **Phase 3** | 필요 시 **소형 VLM**으로 Eye2 `summary_one_line` 생성 추가. 이후 프라이버시(블러/Blind 제스처)는 별도 이슈로 적용. |

이렇게 하면 “Eye1·Eye2 → 정량화 → 27B” 경로가 명확해지고, 27B는 해당 텍스트만 잘 처리하면 이쁜 결과물을 내기 쉬워진다.
