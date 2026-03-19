# 세부 결정 사항 (Detailed Decisions)

이 문서는 프로젝트 구현을 위해 확정된 기술적 의사결정 사항을 기록합니다.

---

## 1. 기술 스택 (Technology Stack) - **[CONFIRMED]**

### 1.1. Frontend State Management
-   **결정**: **Zustand + TanStack Query**
-   **이유**:
    -   **Zustand**: 미쿠의 전역 상태(감정, 현재 행동, 오버레이 위치 등)를 가볍고 직관적으로 관리.
    -   **TanStack Query**: 백엔드(DB, 대화 로그) 데이터의 캐싱, 동기화, 비동기 처리를 효율적으로 담당.
-   **상태**: 확정

### 1.2. LLM Serving Engine
-   **결정**: **ExLlamaV2**
-   **이유**:
    -   RTX 5080의 성능을 극한으로 활용하여 최대 토큰 처리 속도 확보.
    -   남자가 칼을 뽑았으면 속도와 성능이 최우선.
-   **상태**: 확정

### 1.3. TTS 모델
-   **결정**: **GPT-SoVITS**
-   **이유**:
    -   단순한 음성 합성이 아닌, 미쿠의 미묘한 감정선 표현을 위해 고품질 모델 채택.
    -   Secondary GPU (RTX 3090 예정)의 넉넉한 VRAM을 활용하여 고품질 추론 가능.
-   **상태**: 확정

### 1.4. Vector DB
-   **결정**: **PostgreSQL 17+ + pgvector**
-   **이유**:
    -   별도의 Vector DB 솔루션(Chroma 등)을 띄우는 오버헤드 없이, 관계형 데이터(기억 메타데이터)와 벡터 데이터를 하나의 쿼리로 고속 처리.
    -   로컬 환경에서의 I/O 병목 최소화 및 관리 효율성 증대.
    -   PostgreSQL 17 이상에서 지원하는 증분백업(Incremental Backup) 활용.
-   **상태**: 확정

### 1.5. Knowledge Graph
-   **결정**: **Relational Schema (PostgreSQL)**
-   **이유**:
    -   AGE 확장은 복잡도가 높으므로, 우선 잘 설계된 RDB 스키마로 지식 그래프를 표현하고 필요 시 마이그레이션.

---

## 2. 하드웨어 및 메모리 전략 (Hardware & Memory) - **[CONFIRMED]**

### 2.1. GPU 구성
-   **Primary**: **RTX 5080** (Main LLM 전용)
-   **Secondary**: **RTX 3090** (Vision AI, TTS, STT, 3D Rendering) - *3060에서 업그레이드 확정*
-   **전략**: 듀얼 GPU를 적극 활용하여 Main LLM의 추론 속도를 저하시키지 않으면서 고품질 Vision/TTS/렌더링 동시 수행. RTX 5080의 VRAM 부담을 완화하기 위해 Vision AI를 RTX 3090으로 이동.

### 2.2. 메모리 계층 (Memory Hierarchy)
물리적 저장 장치의 특성에 맞춰 데이터를 3단계로 엄격히 분리합니다.

-   **L1 (Short-term)**: **RAM** (시스템 메모리)
    -   현재 진행 중인 대화 컨텍스트, 즉각적인 반응을 위한 데이터.
-   **L2 (Mid-term)**: **SSD (C:)**
    -   Vector DB 인덱스, 최근 며칠간의 기억, 자주 액세스하는 지식.
    -   빠른 RAG 검색을 지원.
-   **L3 (Long-term)**: **HDD (D:)**
    -   **Memory Vault**: 오래된 기억 아카이브, 전체 로그 백업, 학습 데이터셋.
    -   수면 모드 시 L2 데이터를 정리하여 L3로 이관.

---

## 3. 기능 및 UX (Feature & UX) - **[CONFIRMED]**

### 3.1. 윈도우 파쿠르 (Window Parkour)
-   **결정**: **Plugin / Future Update**
-   **내용**: 초기 버전(v0.1)에서는 제외하고, 안정화 후 별도 플러그인 또는 v0.2 스펙으로 개발.

### 3.2. 하드웨어 모니터링 (Suggestion 2)
-   **결정**: **우선 구현 (Core Feature)**
-   **내용**: "미쿠가 컴퓨터 안에 살고 있다"는 컨셉을 위해, CPU/GPU 온도 및 상태를 모니터링하고 반응하는 기능을 우선순위로 개발.
-   **대사 예시**: "오빠, 5080이 너무 뜨거운데? 게임 좀 살살 해."

### 3.3. 미쿠 일기 (Suggestion 1)
-   **결정**: **보류 (Backlog)**
-   **내용**: 추후 고도화 단계에서 고려.

### 3.4. 수면/대기 모드 프레임
-   **결정**: **High Performance Idle**
-   **내용**: RTX 3090의 성능을 믿고, 대기 모드에서도 지나친 프레임 드랍(1fps 등)보다는 자연스러운 움직임(30fps)을 유지하되 리소스 낭비는 방지하는 방향으로 튜닝.

---

## 4. 경로 및 설정 (Paths & Config)

### 4.1. 데이터 경로
-   **Fast Storage (C:)**: `C:/MIKU_DATA/fast_memory/` (DB, Cache)
-   **Vault Storage (D:)**: `D:/MIKU_DATA/vault/` (Archives, Models, Backup)

### 4.2. 모델 경로
-   **LLM/TTS Models**: `D:/MIKU_DATA/models/` (용량이 크므로 HDD에 저장 후 로딩 시 RAM/VRAM으로 적재)

---

## 5. 구현 시 결정 사항 (To Be Decided During Implementation)

### 5.1. 설정값 및 임계값
-   **상태**: 구현하면서 최적값 찾기
-   **항목**:
    -   메모리 계층 이동 임계값 (L1→L2, L2→L3)
    -   기억 검색 임계값 (키워드/벡터 검색 결과 개수 등)
    -   응답 시간 임계값 (Emergency Model 전환 등)
    -   프레임레이트 설정
    -   Vision 캡처 주기

### 5.2. 파일 경로 최적화
-   **상태**: 구현하면서 최적화된 경로 찾기
-   **참고**: 기본 구조는 4장에 명시되어 있으나, 실제 구현 시 I/O 성능 테스트를 통해 최적화

### 5.3. 데이터베이스 스키마
-   **상태**: 구현하면서 설계
-   **예상 테이블**:
    -   기억 관련 테이블
    -   사용자 정보 관련 테이블
    -   비전 모델 관련 테이블 (파일 경로 포함)
-   **참고**: 기존 문서(`docs/backend/db.md`)의 기본 구조를 참고하되, 실제 구현 시 구체화

### 5.4. API 메시지 형식
-   **상태**: 구현하면서 단순화하여 설계
-   **요구사항**:
    -   3D 모델 데이터와 대화 내용을 계속 전송해야 하므로 단순한 구조로 설계
    -   WebSocket 메시지 형식 (JSON 기반)
-   **인증**:
    -   **JWT** 사용 (토큰 기반 인증)
    -   WebSocket 연결 시 하드웨어 주소(MAC Address)로 인증 확인

### 5.5. 프로세스 및 플로우
-   **상태**: 구현 시작할 때 결정
-   **항목**:
    -   대화 처리 플로우 (STT → LLM → TTS 에러 처리)
    -   수면 모드 진입 조건
    -   플러그인 프로세스 통신 방식
    -   갤럭시 워치 연동 프로세스

### 5.6. 3D 상호작용
-   **상태**: 구현하면서 설계
-   **기본 컨셉**:
    -   **모바일**: 터치 기반
        -   터치 → 관심 끌기 (내 말 듣기)
    -   **PC**: 마우스 기반
        -   드래그 → 쓰담쓰담 등
-   **구체적 동작**: 구현하면서 추가

### 5.7. VRAM 관리 전략
-   **기본 할당**:
    -   **RTX 5080 (16GB)**: 언어 모델 (Gemma 3 12B 4-bit) 전용
    -   **RTX 3090 (24GB)**: Vision AI, 렌더링, TTS, STT 등 모든 서브 작업
-   **상태**: 구현하면서 동적 할당 로직 최적화
-   **변경사항**: Vision AI를 RTX 3090으로 이동하여 RTX 5080의 VRAM 부담 완화

### 5.8. 보안 및 프라이버시
-   **민감 정보 처리**: 별도 처리 없음 (개인 사용 환경)
-   **상태**: 구현 시 추가 보안 요구사항이 생기면 반영

### 5.9. 학습 및 개인화
-   **상태**: 별도 문서 참고 (`docs/ai/learning.md`)
-   **파인튜닝**: 점진적 학습 없음. 성격 코어만 학습하며, 갱신이 필요할 때 수동 실행.
-   **개인화**: 기억 검색(L2/L3)으로 프롬프트에 맥락 반영. 수정 시 기억을 가져오는 방식(검색 알고리즘 등)을 조정.

### 5.10. 에러 처리 및 복구
-   **상태**: 구현하면서 설계
-   **참고**: 기본 전략은 `docs/backend/error_logging.md` 참고

---

## 6. 구현 우선순위 (Implementation Priority)

### Phase 1: Core (v0.1)
1.  기본 아키텍처 구축 (Frontend + Backend 연결)
2.  LLM 서빙 (ExLlamaV2 + Gemma 3)
3.  TTS/STT 파이프라인
4.  3D 모델 렌더링 (기본)
5.  하드웨어 모니터링 (Core Feature)

### Phase 2: Memory & Learning
1.  메모리 계층 구현 (L1/L2/L3)
2.  기억 검색 구현 (키워드/벡터, Vector DB 연동 등)
3.  성격 코어용 파인튜닝 파이프라인 (수동 실행, 점진적 학습 없음)

### Phase 3: Enhancement
1.  플러그인 시스템
2.  갤럭시 워치 연동
3.  고급 상호작용 (쓰담쓰담 등)

### Phase 4: Future
1.  윈도우 파쿠르 (Plugin)
2.  미쿠 일기 (Backlog)

### Phase 3+ (모바일 Remote Client)
1.  데스크톱 안정화 후 진행
2.  Android → iOS → iPad/Mac 순서
3.  상세: `docs/planning/09_mobile_platform.md`
