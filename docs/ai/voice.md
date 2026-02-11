# 음성 처리 (Voice Processing)

## 1. 오디오 파이프라인
`Mic Input` -> `Always-on Listen` -> `STT` -> `LLM` -> `TTS` -> `Speaker`

## 2. 호출어 및 제어 (Wake Word & Control)
-   **No Wake Word**: 별도의 호출어("헤이 미쿠") 없이 항상 듣고 있습니다.
-   **Correction (정정)**:
    -   미쿠가 잘못 알아듣거나 의도치 않게 대답했을 때.
    -   사용자: "아니야", "잘못 들었어", "아무것도 아냐".
    -   미쿠: 대화 컨텍스트 삭제 후 대기 모드로 복귀 (Sleep).

## 3. Environmental Sound Detection (환경음 감지)
-   **Target Sounds**: 초인종, 물 끓는 소리, 화재 경보.
-   **Reaction**: 즉시 대화 중단 후 알림.

## 3. Creative Audio (창작)
-   **Humming Composer**: 사용자의 콧노래를 분석해 MIDI/MP3로 변환/저장하는 플러그인.
-   **Auto BGM**: 현재 작업(코딩/게임/휴식)에 맞춰 배경음악 자동 선곡.
-   **Instant Cover**: 유튜브 링크 또는 오디오 입력 -> `yt-dlp` 다운로드 -> 가사/멜로디 분석 -> AI 가창 (즉석 노래 배우기).

## 4. TTS (Text-to-Speech)
-   **Model**: GPT-SoVITS (Miku Finetuned).
-   **Whisper Mode**: 심야 시간 속삭임.
-   **Humming**: 유휴 상태에서 콧노래 흥얼거림.
