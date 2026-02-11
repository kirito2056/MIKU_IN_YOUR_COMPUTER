# 듀얼 비전 시스템 (Dual Vision System)

## 1. 구조
두 개의 '눈'을 통해 사용자와 환경을 인식합니다.

### Eye 1: Webcam (사용자 관찰)
-   **Face Recognition**: 주인(반가움) vs 낯선 사람(경계).
-   **Gesture**: 손 흔들기, 고개 끄덕임, 화면 가리기(Blind).
-   **Posture Check**: 거북목 감지 시 잔소리.
-   **Mimic Mode**: 거울 놀이 (표정 따라하기).
-   **Light Sensor**: 방 불 꺼짐 감지 -> 야광봉 모드.
-   **Ghost Check**: 허공에 얼굴 인식 시 공포 반응.

### Eye 2: Screen Capture (화면 인식)
-   **Game/IDE**: 게임 화면이나 코드 에디터 인식 -> 훈수.
-   **Browser URL**: 검색어 감지 -> 취향 훈수.

## 2. 프라이버시 필터
-   **Blur Logic**: 비밀번호, 카드번호 등 민감 정보 자동 블러 처리.
-   **Blind Gesture**: 손바닥으로 가리면 "안 볼게" 시전.
