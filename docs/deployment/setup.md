# 배포 및 개발 환경 설정 (Deployment & Setup)

## 1. 시스템 요구사항 (Prerequisites)
### Software
-   **OS**: Windows 11 (23H2 이상 권장).
-   **Python**: 3.10 ~ 3.12.
-   **Node.js**: v20 LTS 이상.
-   **CUDA**: Toolkit 12.1+ (for PyTorch & Flash Attention).
-   **FFmpeg**: 필수 (오디오 처리).

### Hardware Check
-   **GPU VRAM**: 최소 8GB (Qwen), 권장 16GB+ (Gemma 12B 4bit).
-   **Storage**: 여유 공간 100GB+ (모델 가중치 및 DB).

## 2. 설치 가이드 (Installation)

### A. Repository Clone
```bash
git clone https://github.com/your-repo/miku-in-your-computer.git
cd miku-in-your-computer
```

### B. Backend Setup
```bash
cd backend
python -m venv venv
./venv/Scripts/activate
pip install -r requirements.txt
# PyTorch with CUDA (반드시 별도 설치 확인)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### C. Frontend Setup
```bash
cd frontend
npm install
# Electron 빌드 도구 설치
npm run postinstall
```

### D. Database Init
-   PostgreSQL 17+ 설치 및 서비스 시작 (증분백업 지원).
-   `pgvector` 익스텐션 활성화: `CREATE EXTENSION vector;`
-   `.env` 파일에 DB 접속 정보 설정.

## 3. 모델 설정 (Model Setup)

### 3.1. 모델 다운로드 및 파인튜닝
-   **프로세스**: 
    1.  기본 모델 수동 다운로드 (Gemma 3, GPT-SoVITS 등)
    2.  파인튜닝 수행 (별도 프로세스)
    3.  파인튜닝 완료된 모델 경로 지정
-   **저장 위치**: `D:/MIKU_DATA/models/`
-   **버전 관리**: Google Drive에 별도 저장 (모델 + 성격 메타데이터 압축)

### 3.2. 첫 실행
-   **초기 설정**: 파인튜닝된 모델 경로를 설정 파일에 지정
-   **첫 만남**: 프로젝트 개요(`docs/planning/01_project_overview.md`)의 "첫 만남" 시나리오 실행

## 4. 실행 (Running)
-   **Dev Mode**: `npm run dev` (Frontend & Backend 동시 실행).
-   **Prod Build**: `npm run dist` (Electron 인스톨러 생성).

## 5. Docker (Optional)
-   **필수 여부**: 필수는 아니지만 개발 환경 통일을 위해 권장
-   **사용 시**: `docker-compose.yml` 참고
-   **Windows 직접 실행**: Docker 없이도 로컬에서 직접 실행 가능
