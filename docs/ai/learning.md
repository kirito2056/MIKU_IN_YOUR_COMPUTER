# 학습 파이프라인 (Learning Pipeline)

## 1. 하이브리드 학습 전략

### A. Threshold Cycle (데이터량 기반)
1.  **Logging**: 대화 로그 실시간 저장.
2.  **Threshold Check**:
    -   누적된 대화 데이터나 학습 데이터 양이 일정 용량(Threshold)을 초과했는지 확인.
    -   용량 초과 시 Fine-tuning 스케줄링.
3.  **Night (Sleep/Learn)**:
    -   **학습**: 스케줄링된 작업이 있다면 Nightly LoRA Fine-tuning 진행 (RTX 5080 사용).
    -   **Backup**: 학습 완료된 모델(LoRA Adapter)은 **Google Drive API**를 통해 클라우드에 버전별 자동 업로드.
    -   **숙면**: 학습할 분량이 없으면 Deep Sleep.

## 2. 자연 성장 시스템 (Natural Growth)
-   **Hidden Stats**:
    -   친밀도, 지식량, 시각 능력, 유머 감각.
-   **Mechanism**:
    -   스탯창 없음. 대화를 통해 자연스럽게 해금되는 기능들.
    -   예: 시각 능력 Lv.5 -> 작은 글씨 읽기 가능.

## 3. Tech Teacher & Knowledge
-   **IT 선생님**: 모르는 용어 질문 시 칠판 꺼내서 설명.
-   **Konami Code**: 히든 커맨드 입력 시 이스터 에그 발동.

## 4. Debugging (투명한 뇌)
-   **Debug Mode**: 화면 구석에 미쿠의 사고 과정(Chain of Thought)을 텍스트로 출력.
