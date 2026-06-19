# 전체 시스템 아키텍처 (System Architecture)

## 1. High-Level Diagram

```mermaid
graph TD
    User[사용자] -->|Voice/Gesture| Client[Frontend (Electron/React/Zustand)]
    User -->|Screen/Webcam| VisionService[Vision AI Service]
    
    subgraph "Local PC (RTX 5080 + RTX 3090)"
        Client -->|WebSocket/HTTP| Server[Backend (FastAPI/ExLlamaV2)]
        
        VisionService -->|Event| Server
        
        Server -->|Prompt| LLM[Gemma 4 12B Server (ExLlamaV2)]
        Server -->|Text| TTS[GPT-SoVITS Engine]
        Server -->|Image Request| SD[Stable Diffusion]
        
        LLM -->|Response| Server
        TTS -->|Audio| Server
        SD -->|Image| Server
        
        Server -->|Store/Retrieve| DB[(PostgreSQL + pgvector)]
        Server -->|Log| Vault[(Memory Vault - HDD)]
    end
    
    Server -->|Response/Action| Client
    Client -->|Render/Audio| User
```

## 2. 모듈별 기술 스택

### Frontend (The Body)
-   **Runtime**: **Electron** (투명 윈도우, 시스템 제어).
-   **Language**: **TypeScript** (v5.0+).
-   **Framework**: **React** + **Vite**.
-   **State Mgmt**: **Zustand** (전역 상태) + **TanStack Query** (서버 데이터).
-   **3D Engine**: **Three.js** (@react-three/fiber).
-   **Audio**: Web Audio API (Spatial PannerNode).

### Backend (The Brain & Nervous System)
-   **Framework**: **FastAPI** (Python).
-   **Protocol**: WebSocket (실시간 대화), REST (설정/상태).
-   **Serving Engine**: **ExLlamaV2** (Maximum Performance).
-   **Hardware Allocation**:
    -   **GPU 0 (RTX 5080)**: Main LLM (ExLlamaV2), Training.
    -   **GPU 1 (RTX 3090)**: Vision AI (Eye1/Eye2 정량화), TTS (GPT-SoVITS), STT, 3D Rendering, Stable Diffusion.
-   **Process Mgmt**: Multiprocessing (AI 모델 별도 프로세스 격리).

### AI Services (The Cortex)
-   **LLM Serving**: **ExLlamaV2** (Optimized for RTX 50-series).
-   **Vision**: `OpenCV` (Motion Detect) + `YOLO` (Object) + 소형 VLM (Eye1/Eye2 정량화).
-   **TTS**: **GPT-SoVITS** (High Quality Emotional TTS).
-   **STT**: `Faster-Whisper` (Local).
-   **Generation**: `Diffusers` (Stable Diffusion).

### Storage (The Memory)
-   **Database**: **PostgreSQL 17+** (Integrated Vector DB, 증분백업 지원).
-   **Extensions**: `pgvector` (Vector Search).
-   **Storage Tiering**:
    -   **L1 (RAM)**: Short-term Context.
    -   **L2 (SSD)**: Mid-term Memory & DB.
    -   **L3 (HDD)**: Long-term Archives (Vault).
