# 3D 캐릭터 시스템 및 기술 명세 (Character System Spec)

## 1. 모델 포맷 (VRM 1.0)
표준화된 휴머노이드 아바타 포맷인 **VRM 1.0**을 사용합니다.
-   **Loader**: `@pixiv/three-vrm` (R3F 호환).
-   **Physics**: `VRMSpringBone` (머리카락, 치마, 넥타이 흔들림).
    -   *설정값*: 중력(Gravity), 강성(Stiffness), 항력(DragForce)을 조절하여 자연스러운 물리 구현.
    -   *충돌 처리*: `VRMSpringBoneCollider`를 다리/가슴에 배치하여 치마 뚫림(Clipping) 방지.

## 2. 블렌드쉐이프 및 표정 (Expression)
VRM 표준 블렌드쉐이프(Morph Targets)를 사용하여 감정과 립싱크를 표현합니다.

### A. 립싱크 (Lip Sync)
-   **Vowel**: `aa`, `ih`, `ou`, `ee`, `oh` (AIUEO).
-   **Algorithm**: TTS 오디오 스트림의 진폭/주파수 분석 또는 Phoneme 추출 데이터를 기반으로 실시간 가중치 보간(Lerp).

### B. 감정 표현 (Emotion Presets)
-   **Basic**: `Neutral`, `Happy`, `Angry`, `Sorrow`, `Fun`.
-   **Custom**:
    -   `Sleep` (눈 감고 평온).
    -   `Surprised` (눈 크게, 입 벌림).
    -   `Mence` (죽은 눈 - 얀데레/협박 모드).

## 3. 애니메이션 시스템 (Animation System)
-   **Retargeting**: Mixamo 등 외부 애니메이션(`FBX`)을 VRM 본 구조에 맞춰 실시간 리타겟팅.
-   **Blending**: 동작 전환 시 `AnimationMixer`를 사용해 0.5초간 부드럽게 블렌딩(Fade In/Out).
-   **Layered Animation**:
    -   *하체*: 걷기/뛰기.
    -   *상체*: 손 흔들기/가리키기 (하체 동작 유지).
-   **Inverse Kinematics (IK)**:
    -   **Head LookAt**: 사용자의 얼굴/마우스 커서를 응시.
    -   **Hand Reach**: 특정 아이콘이나 창을 가리키는 손 동작 보정.
