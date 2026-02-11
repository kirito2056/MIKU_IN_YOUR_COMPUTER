# 요구사항 정의서 (Requirements)

## 1. 하드웨어 요구사항 (Target Spec)
-   **CPU**: AMD Ryzen 9 **7950X3D** (연산 & 게이밍 & WebSocket 처리).
-   **Motherboard**: **X870E** 또는 **X670E** (Dual GPU 간섭 없는 모델, 예: ProArt/Crosshair).
-   **GPU (Dual Setup)**:
    -   **Primary (RTX 5080 16GB)**: Main LLM (Gemma 3 27B 4-bit), Vision AI.
    -   **Secondary (RTX 3090 24GB)**: TTS(GPT-SoVITS), STT, 3D Rendering, Small LLM.
-   **RAM**: DDR5 **32GB** 이상 (권장 64GB).
-   **Storage**:
    -   **SSD (C:)**: 시스템, 단기/중기 기억 (PostgreSQL/pgvector).
    -   **HDD (D:)**: **[Memory Vault]** 장기 기억 아카이브, 모델 파일.
-   **Network**: Google Drive (모델 백업용).

## 2. 기능 요구사항 (Functional)
-   **Always-on-Top**: 다른 창 위에 항상 표시 (투명 배경).
-   **Natural Growth**: 사용에 따라 자연스럽게 해금되는 기능.
-   **Offline First**: 인터넷 없이도 핵심 기능 동작.
-   **Dual Vision**: 웹캠(사용자) + 화면 캡처(컨텍스트) 동시 분석.
-   **Hybrid Learning**: 낮에는 로그 수집, 밤에는 미세 조정(Fine-tuning).

## 3. 비기능 요구사항 (Non-Functional)
-   **Latency**: 음성 응답 지연 1초 이내 (Local LLM 최적화).
-   **Safety**: 2038년 문제 등 시스템 이슈 대응.
-   **Extensibility**: 민감 정보 필터링 등은 Core가 아닌 **Plugin**으로 구현.