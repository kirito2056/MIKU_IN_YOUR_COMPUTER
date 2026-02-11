# 플러그인 시스템 & SDK (Plugin System)

## 1. 아키텍처 (Architecture)
미쿠는 **Manifest 기반의 모듈러 시스템**을 사용합니다. 각 플러그인은 독립된 프로세스 또는 샌드박스 내에서 실행되며, Core API를 통해 미쿠와 통신합니다.

### 구조 (Structure)
-   **Manifest (`manifest.json`)**: 플러그인 메타데이터, 권한 요청, 진입점 정의.
-   **Backend (Python)**: `FastAPI` 라우터 확장, 백그라운드 작업, 하드웨어 제어.
-   **Frontend (React)**: 오버레이 UI 컴포넌트, 설정 패널.

### 프로세스 격리 (Process Isolation)
플러그인 오류가 메인 시스템에 영향을 주지 않도록 격리합니다.
-   **독립 프로세스**: 각 플러그인은 별도 Python 프로세스로 실행.
-   **에러 핸들링**: 플러그인 크래시 시 자동 재시작 (최대 3회) 또는 비활성화.
-   **리소스 제한**: CPU/메모리 사용량 제한 (플러그인별 설정 가능).
-   **통신**: 프로세스 간 통신은 WebSocket 또는 Named Pipe 사용.
-   **로깅**: 플러그인 오류는 별도 로그 파일에 기록 (메인 시스템 로그와 분리).

## 2. 권한 시스템 (Permission Model)
사용자는 각 플러그인 설치 시 권한을 승인해야 합니다.
-   `miku.permission.HARDWARE`: CPU/GPU 센서 접근.
-   `miku.permission.NETWORK`: 외부 API 통신 (디스코드, 날씨 등).
-   `miku.permission.FILE_SYSTEM`: 특정 폴더 읽기/쓰기.
-   `miku.permission.OVERLAY`: 화면에 UI 그리기.

## 3. 공식 플러그인 (Official Plugins)

### A. Minecraft Bot (Mineflayer)
-   **기능**: 사용자와 멀티플레이 서버에 함께 접속.
-   **행동**: 사용자를 따라다님(Follow), 자원 채집, 집 짓기 보조.
-   **연동**: 게임 내 채팅을 STT/TTS로 변환하여 음성 대화.

### B. Discord Proxy
-   **기능**: 디스코드 봇으로 위장하여 메시지 송수신.
-   **행동**: "미쿠야" 멘션 시 답변, 친구들이랑 노가리 까기.
-   **VC**: 보이스 채널에 접속하여 노래 부르기 가능.

### C. Smart Home (IoT)
-   **기능**: Home Assistant / Philips Hue 연동.
-   **행동**: "불 꺼줘" -> 소등 후 "잘 자, 오빠." (야광봉 모드 전환).

### D. Hardware Monitor
-   **기능**: `LibreHardwareMonitor` 연동.
-   **행동**: CPU 온도 90도 돌파 시 -> "오빠, 나 머리가 너무 뜨거워..." (걱정/경고).

### E. Reminder & Calendar
-   **기능**: 사용자 기존 앱 API 연동.
-   **행동**: "3시에 회의 있잖아, 안 가?" (잔소리 모드).

### F. Humming Composer
-   **기능**: 사용자의 콧노래(Humming) 녹음 -> MIDI 변환 -> 편곡.
-   **출력**: 미쿠가 해당 멜로디를 가사 붙여서 불러줌.

## 4. SDK Hooks
-   `onWakeWord(text)`: 호출어 감지 시.
-   `onVisionDetect(objects)`: 특정 사물/사람 인식 시.
-   `onSystemEvent(event)`: 부팅, 절전, 배터리 부족 등.

## 5. 플러그인 개발 가이드 (Plugin Development Guide)
-   **상태**: 계획 단계 (구현 시 구체화 예정)
-   **내용**: 
    -   Manifest 작성 방법
    -   Backend/Frontend 플러그인 구조
    -   API 사용 예제
    -   권한 요청 및 처리
    -   테스트 방법
