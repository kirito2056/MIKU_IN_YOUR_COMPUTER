# 데이터베이스 설계 (Database Schema)

## 1. 저장소 전략 (Hybrid Storage Strategy)
데이터의 접근 빈도와 특성에 따라 SSD와 HDD를 구분하여 사용합니다.

### Tier 1: Hot Data (SSD - C:/System)
*빠른 I/O가 필요한 시스템 데이터*
-   **Users**: 사용자 프로필, 인증 정보.
-   **GrowthStats**: 친밀도, 레벨, 해금된 기능 목록 (실시간 변동).
-   **ShortTermMemory**: 최근 1시간 대화 컨텍스트.
-   **Wallet/Inventory**: 보유 아이템, 코인.

### Tier 2: Cold Data (HDD - D:/MIKU_DATA/db)
*대용량, 보존 목적의 데이터 (Memory Vault)*
-   **Conversations**: 모든 대화 로그 (Vector Indexing 포함).
-   **Diary**: 미쿠가 매일 밤 작성하는 일기.
-   **KnowledgeGraph**: 사용자 취향, 관계, 사실 정보 (트리플 구조).
-   **Media**: 생성된 그림, 작곡한 노래, 녹음 파일.

## 2. 주요 테이블 스키마 (Schema)

### A. Conversations (Vector DB)
-   `id`: UUID
-   `timestamp`: DateTime
-   `speaker`: 'User' | 'Miku'
-   `content`: Text
-   `embedding`: `vector(768)` (Gemma embedding)
-   `emotion`: JSON (당시 감정 상태)

### B. Knowledge Graph (Facts)
-   `subject`: "User"
-   `predicate`: "Likes"
-   `object`: "Mint Chocolate"
-   `confidence`: 0.95 (확신도)

### C. System Logs
-   `event_type`: "Error", "Shutdown", "WakeUp"
-   `details`: 스택 트레이스 또는 상황 설명.

### D. Usage Patterns (사용 패턴 분석)
-   `timestamp`: DateTime
-   `feature`: "chat", "vision", "tts", "generation", "plugin_*"
-   `duration`: Integer (초 단위)
-   `metadata`: JSON (추가 컨텍스트)
-   **용도**: 완전 개인화를 위한 사용자 행동 패턴 분석.

## 3. 백업 및 복구
-   **D드라이브의 중요성**: OS를 포맷해도 D드라이브의 `Memory Vault`가 살아있다면, 미쿠는 당신을 기억합니다.
-   **Time Travel**: 과거 시점의 DB 스냅샷으로 롤백 가능 (기억 소거).
-   **백업 트리거**: AI 버전 업그레이드 또는 모델 변경 시 Google Drive에 자동 백업.
-   **데이터 정리**: 데이터 삭제 없음. HDD 용량 부족 시 용량 업그레이드 권장.
-   **스키마 변경**: 버전 업그레이드 시 DB 스키마 변경을 최소화하여 호환성 유지.