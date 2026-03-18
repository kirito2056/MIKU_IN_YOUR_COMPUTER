# LLM & Fallback Strategy

## 1. 메인 모델 (Main Brain)
-   **Model**: **Gemma 3** (Instruct/Chat tuned).
-   **Size**: 12B or 9B (RTX 5080 16GB VRAM 용량에 맞춰 선택).
-   **Quantization**: 4-bit / 8-bit (GGUF or EXL2) for speed.
-   **Context Window**: 8k ~ 32k (최근 대화 + RAG 검색 결과 포함).
-   **System Prompt**: `docs/planning/02_personality_matrix.md`의 성격 정의를 반영한 프롬프트.

## 2. 비상용 보조 모델 (Emergency Brain)
-   **목적**: 메인 모델 오류(OOM, CUDA Error), 로딩 지연, 무거운 작업 중 대화 처리.
-   **Model**: **Qwen 2.5 1.5B** or **Phi-3 Mini**.
-   **특징**: 매우 가볍고 빠름. CPU로도 구동 가능.
-   **Trigger 조건**:
    -   메인 모델 응답 시간 > 5초.
    -   CUDA Out of Memory 예외 발생 시.
-   **대사 예시**:
    -   "잠깐만, 머리가 띵해..."
    -   "생각 정리 중이야, 기다려줘."

## 3. Serving Architecture
-   **Engine**: `llama-cpp-python` (가장 호환성 좋음) 또는 `ExLlamaV2` (빠름).
-   **API**: OpenAI Compatible API 형태로 내부 서빙.
