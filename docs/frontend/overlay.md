# 프론트엔드 오버레이 기술 (Overlay Technology)

## 1. Electron 투명 윈도우 (Transparent Window)
-   **Click-Through**: 평소에는 마우스 이벤트를 통과시켜(Pass-through) 바탕화면 아이콘이나 뒤쪽 창을 클릭할 수 있게 함.
-   **Interactive Area**: 미쿠의 3D 모델이 있는 영역만 마우스 이벤트를 캡처(`setIgnoreMouseEvents` 동적 제어).

## 2. 물리 엔진 및 상호작용 (Physics & Interaction)
-   **Window Parkour**:
    -   `Win32 API` (`EnumWindows`, `GetWindowRect`)를 통해 현재 열린 모든 창의 좌표 수집.
    -   창의 상단바(Title Bar)를 '바닥(Ground)'으로 인식하여 점프 및 착지.
-   **Desktop Icons**:
    -   바탕화면 아이콘의 핸들을 얻어 좌표 추적.
    -   미쿠가 발로 차면 아이콘 위치를 변경(`LVM_SETITEMPOSITION`).

## 3. 렌더링 최적화
-   **Language**: TypeScript (Type Safety & Autocomplete).
-   **Library**: React Three Fiber (R3F), Drei.
-   **Performance**:
    -   프레임 제한 (평소 30fps, 상호작용 시 60fps+).
    -   GPU 리소스가 게임에 우선 할당되도록 `Low Priority` 모드 지원.

## 5. Multi-Platform Support (Mac/Remote)
-   **Mode**: `Standalone` (Windows) vs `Remote Client` (Mac).
-   **Remote Client Logic**:
    -   **Vision**: Mac의 화면 (`ScreenCaptureKit`) 및 웹캠 프레임을 1fps(평상시) ~ 5fps(대화중)로 캡처하여 Windows 서버로 전송.
    -   **Audio**: 마이크 입력을 `Opus` 코덱으로 실시간 인코딩하여 전송.
    -   **Rendering**: Windows 서버로부터 받은 감정/행동 지시(Action Packet)에 따라 로컬(Mac)에서 3D 모델 렌더링.
    -   **No Physics**: Mac에서는 창 밟기(Parkour) 기능을 비활성화하거나, 제한적인 물리 효과만 적용.
