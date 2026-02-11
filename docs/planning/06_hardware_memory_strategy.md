# 하드웨어 구성 및 메모리 전략 (Hardware & Memory Strategy)

## 1. 하드웨어 구성 (Hardware Configuration)

### 1.1. 메인보드 및 시스템 (Infrastructure)
*   **Motherboard**: **X870E** 칩셋 기반 (E-ATX 또는 High-end ATX 권장).
    *   **필수 조건**: Dual GPU(RTX 5080 + RTX 3060) 장착 시 물리적 간섭이 없는 **넓은 PCIe 슬롯 간격(4-slot spacing)** 또는 최하단 x16 슬롯 지원 모델.
    *   *예시 모델*: ASUS ProArt X670E-CREATOR, ROG CROSSHAIR 시리즈 등.
*   **CPU**: AMD Ryzen 9 **7950X3D** (L3 캐시를 통한 연산 가속).
*   **RAM**: DDR5 **32GB** 이상 (64GB 권장).

### 1.2. GPU 역할 분담 (Dual GPU Strategy)
VRAM 효율성과 반응 속도를 최적화하기 위해 두 GPU의 역할을 철저히 분리합니다.

| GPU | 모델 | VRAM | 할당된 역할 (Roles) | 비고 |
| :--- | :--- | :--- | :--- | :--- |
| **GPU 0 (Main)** | **RTX 5080** | **16GB** | **Main Brain (LLM)**, **Vision AI** | GDDR7 초고속 메모리 활용. **ExLlamaV2** 기반 고속 추론. |
| **GPU 1 (Sub)** | **RTX 3090** | **24GB** | **TTS** (GPT-SoVITS), **STT**, **3D Rendering** | **3060에서 업그레이드 확정**. 고품질 TTS 및 렌더링 전담. |

### 1.3. 하드웨어 확장 전략 (Future Expansion)
**현재 상태**: RTX 5080(Main) 설치됨. Sub GPU로 RTX 3090 확보 예정(사실상 확정).

#### 확정 시나리오: RTX 3090 추가 (Dual GPU)
-   **구성**: RTX 5080 (Main) + RTX 3090 (Sub)
-   **이점**:
    -   RTX 3090의 **24GB VRAM**은 신의 한 수.
    -   GPT-SoVITS (High Quality) 구동에도 여유로움.
    -   Stable Diffusion XL 등 고해상도 생성 모델 상시 대기 가능.
-   **할당 전략**:
    -   **GPU 0 (RTX 5080)**: Main LLM (Gemma 3 27B 4-bit) + Vision AI
    -   **GPU 1 (RTX 3090)**: TTS(GPT-SoVITS) + STT + SDXL + 3D Rendering + Hardware Monitor

---

## 2. LLM 모델 전략 (Model Strategy)

### 2.1. Main Model (RTX 5080)
*   **Target Model**: **Gemma 3 27B** (Instruct tuned).
*   **Quantization**: **4-bit GGUF/EXL2**.
    *   *이유*: 16-bit(54GB)나 8-bit(28GB)는 로드 불가능. 4-bit(약 16~17GB)가 한계선이자 최적점.
    *   *특징*: Gemma 3는 멀티모달(Vision) 능력이 강화되어, 별도의 Vision 모델 없이도 이미지 이해 가능성이 높음.
*   **Context Window**: 4k ~ 8k (VRAM 잔여량에 따라 가변적).

### 2.2. Sub/Emergency Model (RTX 3060)
*   **Target Model**: **Qwen 2.5 1.5B** or **Phi-3 Mini**.
*   **용도**: Main Model 로딩 중 대화, 단순 인사, 시스템 알림 등 "즉답"이 필요한 상황.

---

## 3. 메모리 계층 아키텍처 (Memory Hierarchy Architecture)

인간의 기억 구조를 모방하여 저장 매체의 속도에 따라 3단계로 기억을 관리합니다. 이를 통해 **VRAM 오버헤드 없이 무한한 기억(Infinite Context)**을 구현합니다.

### 3.1. 계층별 정의

| 계층 (Level) | 저장 매체 (Storage) | 데이터 형태 (Data Type) | 속도 | 역할 및 동작 방식 |
| :--- | :--- | :--- | :--- | :--- |
| **L1. 단기 기억**<br>(Short-term) | **RAM**<br>(System Memory) | Python List / Redis | 매우 빠름 | - 최근 대화 로그 (Recent 10~20 turns).<br>- 대화 시 **즉시 프롬프트에 포함**되어 VRAM으로 전송됨.<br>- 휘발성 (전원 꺼지면 사라짐). |
| **L2. 중기 기억**<br>(Mid-term) | **SSD (C:)**<br>(Vector DB) | **PostgreSQL + pgvector** | 빠름 | - 오늘 하루의 요약, 중요한 사실.<br>- **유사도 검색(RAG)**을 통해 관련 내용만 추출하여 L1으로 승격.<br>- 반영구적 저장. |
| **L3. 장기 기억**<br>(Long-term) | **HDD (D:)**<br>(Memory Vault) | SQLite / JSONL / Backup | 느림 | - 과거 대화 아카이브, 사용자 프로필.<br>- **Batch Job**(수면 모드)으로 L2 데이터를 정리/압축하여 저장.<br>- 필요 시에만 검색. |

### 3.2. 구동 프로세스 (Stateless Execution Loop)

**"새로운 대화창을 매번 여는 것과 같은"** 방식으로 VRAM 누수를 원천 차단합니다.

1.  **Input (청각)**:
    *   사용자 음성 -> STT -> 텍스트 변환 -> **RAM(L1)**에 저장.
2.  **Context Construction (회상)**:
    *   RAM에서 `[최근 대화]` 가져오기.
    *   SSD(L2)/HDD(L3)에서 `[관련된 기억]` 검색하여 가져오기.
    *   **Prompt 구성**: `System Prompt` + `Retrieved Memory` + `Recent Dialogue`.
3.  **Inference (생각)**:
    *   구성된 Prompt를 **RAM -> VRAM(RTX 5080)**으로 고속 복사 (Context Loading).
    *   LLM 추론 수행 -> 답변 생성.
    *   **추론 종료 즉시 VRAM 내의 Context 해제 (Stateless)**.
4.  **Output & Archive (발화 및 기억)**:
    *   답변을 TTS로 출력 및 **RAM(L1)**에 저장.
    *   대화가 길어지면 L1 데이터를 요약하여 L2(SSD)로 이동시키고 L1 비우기 (**Context Sliding**).
