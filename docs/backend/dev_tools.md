# 개발 도구 (Development Tools)

## 1. 로그 뷰어 (Log Viewer)

### 1.1. 요구사항
-   **필수**: 로그 파일을 실시간으로 확인할 수 있는 도구 필요
-   **기능**:
    -   로그 레벨별 필터링 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    -   카테고리별 필터링 (LLM, TTS, Vision, GPU 등)
    -   실시간 로그 스트리밍
    -   검색 기능
    -   JSON 로그 파싱 및 시각화

### 1.2. 구현 방안
-   **옵션 A**: Electron 앱 내장 로그 뷰어 (별도 창)
-   **옵션 B**: 웹 기반 로그 뷰어 (FastAPI 엔드포인트)
-   **옵션 C**: 기존 로그 뷰어 도구 활용 (예: `lnav`, `glogg`)

---

## 2. 성능 프로파일러 (Performance Profiler)

### 2.1. 요구사항
-   **권장**: 성능 병목 지점 파악을 위한 프로파일링 도구
-   **기능**:
    -   LLM 추론 시간 측정
    -   TTS/STT 처리 시간
    -   GPU/CPU 사용률 모니터링
    -   메모리 사용량 추적
    -   프레임레이트 모니터링 (Frontend)

### 2.2. 구현 방안
-   **Python**: `cProfile`, `line_profiler`, `memory_profiler`
-   **GPU**: `nvidia-smi` 로그 분석, PyTorch Profiler
-   **Frontend**: React DevTools Profiler, Chrome DevTools Performance
-   **UI**: 프로파일링 결과를 시각화하는 관리자 도구

---

## 3. DB 관리 도구 (Database Management Tool)

### 3.1. 요구사항
-   **필수**: 관리자용 웹 인터페이스
-   **기능**:
    -   데이터베이스 스키마 확인
    -   테이블 데이터 조회/수정/삭제
    -   벡터 검색 테스트
    -   쿼리 실행 및 결과 확인
    -   데이터 백업/복구

### 3.2. 구현 방안
-   **기술 스택**: 
    -   FastAPI 기반 관리자 API
    -   React 기반 웹 UI (별도 관리자 페이지)
-   **인증**: 관리자 전용 인증 (JWT 또는 별도 키)
-   **접근**: `http://localhost:8000/admin` (또는 별도 포트)

---

## 4. 개발 모드 vs 프로덕션 모드

### 4.1. 개발 모드
-   **로그 레벨**: DEBUG 포함
-   **에러 상세 정보**: 스택 트레이스 표시
-   **Hot Reload**: 코드 변경 시 자동 재시작
-   **디버그 UI**: Chain of Thought 표시 등

### 4.2. 프로덕션 모드
-   **로그 레벨**: INFO 이상 (DEBUG 제외)
-   **에러 처리**: 사용자 친화적 메시지
-   **성능 최적화**: 불필요한 디버깅 코드 제거
-   **보안**: 민감 정보 마스킹

---

## 5. 통합 개발 환경

### 5.1. 권장 도구
-   **IDE**: VS Code (Python, TypeScript 지원)
-   **확장 프로그램**:
    -   Python (Pylance, Python Debugger)
    -   TypeScript/JavaScript
    -   Docker (선택)
    -   Git
-   **터미널**: 통합 터미널에서 Backend/Frontend 동시 실행

### 5.2. 디버깅
-   **Backend**: Python 디버거 (VS Code 내장)
-   **Frontend**: Chrome DevTools (Electron)
-   **통합**: WebSocket 연결 상태 확인 도구
