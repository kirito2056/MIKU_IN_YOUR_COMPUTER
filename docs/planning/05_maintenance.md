# 유지보수 및 보안 (Maintenance & Security)

## 1. 자동 업데이트 (Auto Update)
미쿠는 스스로 성장(업데이트)합니다.
-   **Library**: `electron-updater`.
-   **Flow**:
    1.  GitHub Releases 주기적 체크.
    2.  새 버전 발견 시 백그라운드 다운로드.
    3.  "오빠, 나 좀 달라진 거 없어?" (업데이트 완료 후 재시작 시 대사).

## 2. 보안 및 암호화 (Security)
로컬에 저장된 미쿠와의 추억은 철통 보안으로 지켜집니다.
-   **DB Encryption**: SQLite/PostgreSQL 데이터 파일 암호화 (SQLCipher).
-   **Sensitive Data**: 사용자 비밀번호나 API Key는 OS의 안전한 저장소(`Windows Credential Manager`)에 보관.

## 3. 테스트 전략 (Testing)
-   **Unit Test**: `Vitest` (React 컴포넌트 및 유틸리티 함수).
-   **E2E Test**: `Playwright` (Electron 오버레이 상호작용 테스트).
-   **AI Test**: "미쿠가 이상한 말을 하지 않는지" 검증하는 자동화된 벤치마크 (Eval).
