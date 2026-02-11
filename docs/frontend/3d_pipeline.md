# 3D Asset Pipeline (VRM Workflow)

## 1. Overview
본 프로젝트는 3D 캐릭터 운용을 위해 **VRM 1.0** 표준을 채택합니다.
Blender에서 제작된 모델을 VRM으로 변환하고, React(Three.js)에서 로드하여 애니메이션과 물리를 적용하는 전체 공정을 정의합니다.

## 2. Tools Required
-   **Blender 4.x**: 모델링 및 리깅 수정.
-   **VRM Add-on for Blender**: VRM 포맷 내보내기용 플러그인.
-   **Mixamo**: 기본 애니메이션 소스 (Idle, Walk, Sit 등).

## 3. Workflow Steps

### Step 1: Blender Setup & Rigging
1.  **Bone Structure**: VRM Humanoid 표준 본 구조(Hips, Spine, Chest, Neck, Head...)를 준수해야 합니다.
2.  **T-Pose**: 내보낼 때는 반드시 T-Pose 상태여야 합니다.
3.  **Blendshapes (Shape Keys)**:
    -   필수: `A`, `I`, `U`, `E`, `O` (립싱크용).
    -   필수: `Blink`, `Joy`, `Angry`, `Sorrow`, `Fun` (감정 표현용).
    -   선택: `LookUp`, `LookDown`, `LookLeft`, `LookRight` (시선 처리).

### Step 2: Physics (SpringBone) Setup
VRM의 가장 강력한 기능인 **SpringBone**을 설정하여 머리카락과 의상 움직임을 구현합니다.
1.  **Secondary Bones**: 머리카락, 넥타이, 치마, 소매 등에 물리용 Bone이 심어져 있어야 합니다.
2.  **VRM Extension 설정**:
    -   Blender VRM 탭에서 `SpringBone` 콜라이더(Collider) 그룹 설정.
    -   Head, Chest, Legs에 Collider를 넣어 머리카락/치마가 몸을 뚫지 않게 설정.
    -   **Drag Force**와 **Stiffness** 조절로 '찰랑거림' 느낌 튜닝.

### Step 3: Material & Shader (MToon)
1.  VRM은 **MToon** 쉐이더(애니메이션 스타일)를 사용합니다.
2.  Blender의 Principled BSDF 대신 VRM MToon 설정을 사용하여 그림자(Shade Color)와 림 라이트(Rim Light)를 지정합니다.

### Step 4: Export
-   Format: `VRM 1.0`
-   Path: `frontend/public/models/miku_v1.vrm`

## 4. Animation Retargeting (Mixamo to VRM)
Mixamo 애니메이션(.fbx)은 실사 비율이라 미쿠에게 바로 입히면 어색합니다 (어깨 넓어짐, 발 미끄러짐).

### Option A: Runtime Retargeting (추천)
-   `three-vrm`의 헬퍼 기능을 사용하거나, `Mixamo` 애니메이션의 Bone Name을 VRM Bone Name으로 매핑하여 실시간으로 적용.
-   장점: 애니메이션 파일을 수정할 필요 없음.

### Option B: Blender Retargeting
1.  Blender에서 Mixamo FBX 임포트.
2.  미쿠 Armature에 맞춰 애니메이션 베이크(Bake).
3.  GLB/VRM 애니메이션 클립으로 별도 저장.

## 5. Implementation in React
```jsx
// Pseudo Code for loading VRM
import { useGLTF } from '@react-three/drei'
import { VRMLoaderPlugin } from '@pixiv/three-vrm'

function MikuModel() {
  const { scene } = useGLTF('/models/miku_v1.vrm', (loader) => {
    loader.register((parser) => new VRMLoaderPlugin(parser))
  })
  
  // SpringBone Update Loop
  useFrame((state, delta) => {
    if (vrm.current) {
      vrm.current.update(delta) // 물리 효과 계산
    }
  })

  return <primitive object={scene} />
}
```
