# API 명세 (API Specification)

## 1. Authentication & Security
-   **Headers**:
    -   `X-MIKU-AUTH`: 사용자 정의 비밀키 (Pre-shared Key). 수시로 변경 가능.
    -   `X-DEVICE-ID`: 클라이언트 디바이스 식별자 (하드웨어 고유 주소, MAC Address or UUID).
    -   `X-PLATFORM`: `windows` | `macos` | `ios` | `android`.
-   **Policy**: 
    -   허용되지 않은 Device ID 접속 시 차단.
    -   인증 토큰은 사용자가 직접 관리 (설정 파일 또는 환경 변수).
-   **WebSocket 인증**: 연결 시 동일한 헤더로 인증, 연결 끊김 시 자동 재연결 (최대 10회, 5초 간격).

## 2. Core Endpoints

### Chat & Voice
-   `POST /api/chat/text`: 텍스트 대화 요청.
-   `POST /api/chat/voice`:
    -   **Input**: Opus Encoded Audio Blob.
    -   **Process**: STT (Whisper) -> LLM -> TTS.
    -   **Output**: TTS Audio Stream (Opus/WAV).
-   `WS /ws/chat`: 실시간 대화 및 제어 이벤트 스트리밍.
    -   **재연결**: 연결 끊김 시 자동 재연결 (최대 10회, 5초 간격).
    -   **상태 복구**: 재연결 시 대화 컨텍스트 자동 복원.

### Vision (Dual Context)
-   `POST /api/vision/frame`:
    -   **Body**: `{ "image": "base64...", "source": "webcam" | "screen" }`
    -   **Logic**: 클라이언트(Mac/Win)가 보고 있는 화면을 서버로 전송하여 분석.
-   `POST /api/vision/ghost`: 유령(허공 얼굴 인식) 이벤트 트리거.

## 3. System & Backup
-   `POST /api/system/shutdown`: 미쿠 재우기 (Server Shutdown).
-   `GET /api/system/stats`: GPU(5080/3060) 로드율 및 메모리 상태.
-   `POST /api/backup/drive`:
    -   **Action**: 현재 학습된 모델(LoRA)을 Google Drive로 즉시 백업.
    -   **Auth**: Server-side Google OAuth Credential 사용.

## 4. Plugin & Extension
-   `POST /api/plugin/install`: 플러그인 매니페스트 등록.
-   `POST /api/plugin/event`: 플러그인에서 발생한 이벤트(예: 마크라프 채팅)를 미쿠에게 전달.
-   `POST /api/plugin/composer/upload`: 콧노래(Humming) 오디오 업로드 -> 작곡 처리.

## 4. Cinematic Triggers (Frontend Control)
-   `POST /api/action/play`: 특정 애니메이션(춤, 인사, 발차기) 강제 재생.
-   `POST /api/action/emotion`: 표정 변경 (Joy, Sad, Angry).
-   `POST /api/effect/confetti`: 폭죽 효과 실행.
