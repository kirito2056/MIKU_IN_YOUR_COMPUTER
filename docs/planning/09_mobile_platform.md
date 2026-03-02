# 모바일 플랫폼 기획 (Mobile Platform - iOS/Android)

데스크톱(Windows) 안정화 이후, 모바일(iOS/Android) 및 태블릿(iPad), Mac(MacBook/Mac mini)에서도 미쿠와 교감할 수 있도록 하는 Remote Client 아키텍처를 정의합니다.

---

## 1. 개발 우선순위

| 순서 | 플랫폼 | 비고 |
|------|--------|------|
| 1 | **데스크톱 (Windows)** | 먼저 안정화 |
| 2 | **모바일 (Android)** | 외부 접속 지원, Android 우선 |
| 3 | **모바일 (iOS)** | Android 안정화 후 |
| 4 | **태블릿/Mac** | iPad, MacBook, Mac mini (경량화된 클라이언트) |

---

## 2. 갤럭시 워치 역할

-   **역할**: 사용자 상태 측정용 **추가 센서**
-   **용도**: 심박수, 활동량, 수면 등 웹캠/화면 캡처로 얻지 못하는 데이터 수집
-   **연동**: 워치 앱 → 데이터 수집 → Backend API로 전송
-   **상세**: `docs/backend/monitoring.md` 4.1절 참고

---

## 3. 기능 범위

-   **목표**: 데스크톱과 최대한 비슷하게 구현
-   **포함**:
    -   채팅 (텍스트/음성)
    -   풀 3D 미쿠 렌더링
    -   **Dual Vision**: 화면 캡처 + 웹캠 (둘 다 지원)
-   **웹캠**: 프라이버시를 위해 **온/오프 토글** 기능 추가 (외부에서 다른 사람이 볼 수 있음)
-   **제외**:
    -   창 파쿠르, 바탕화면 아이콘 등 데스크톱 전용 물리/시스템 상호작용

---

## 4. 네트워크 & 외부 접속

### 4.1. 요구사항

-   **외부 접속**: 같은 WiFi뿐 아니라 **4G/5G 등 외부**에서도 PC Backend에 접속 가능해야 함

### 4.2. 구성

-   **nginx** 설치 후 **포트 포워딩**으로 WebSocket/HTTP 접속 허용
-   **인증**: HTTP 헤더 기반
    -   `X-MIKU-AUTH`: Pre-shared Key (토큰)
    -   `X-DEVICE-ID`: 하드웨어 고유 주소 (MAC Address 또는 UUID)
    -   `X-PLATFORM`: `android` | `ios` | `ipados` | `macos`
-   허용되지 않은 Device ID 접속 시 차단

### 4.3. 배포

-   **앱 스토어 배포**: ❌ 없음
-   **용도**: 완전 내부용, 개인 전용

---

## 5. 기술 스택

### 5.1. 빌드 방식

-   **선호**: 3D + 게임 등 부하가 있으므로 **경량화**된 방식
-   **대상**: Android, iOS, iPad, MacBook, Mac mini
-   **후보**: Capacitor (웹 기반 패키징) 또는 React Native
-   **결정**: 구현 시 성능/호환성 검증 후 확정

### 5.2. 코드 공유

-   **API**: 공유 (동일한 REST/WebSocket 엔드포인트)
-   **상태**: 공유 가능한 부분만 (Zustand store, TanStack Query 로직 등)
-   **JSON 응답 형식**: 동일하게 유지
-   **플랫폼별 차이 허용**:
    -   경량화 (모바일 vs 데스크톱)
    -   DB/저장 방식 (로컬 SQLite vs IndexedDB 등)

---

## 6. UX & 동작

### 6.1. 앱 생명주기

-   **Always-on**: 앱이 **포그라운드에 있는 동안** 항상 연결 유지
-   백그라운드 전환 시 연결 해제 또는 절전 모드 (플랫폼 제한 고려)

### 6.2. Vision (화면/웹캠)

-   **화면 캡처**: 지원 (플랫폼 API 사용)
-   **웹캠**: 지원 + **온/오프 토글** (프라이버시)

---

## 7. 구현 Phase (참고)

| Phase | 내용 |
|-------|------|
| Phase 1 | 데스크톱 Core 안정화 |
| Phase 2 | Memory & Learning |
| Phase 3 | 플러그인, 갤럭시 워치, 고급 상호작용 |
| **Phase 3+** | **모바일 Remote Client (Android → iOS → iPad/Mac)** |

---

## 8. 관련 문서

-   `docs/frontend/overlay.md` - Mac Remote Client 로직 (모바일도 유사)
-   `docs/backend/api.md` - 인증 헤더, X-PLATFORM
-   `docs/backend/monitoring.md` - 갤럭시 워치 연동

*Last Updated: 2026-03-02*
