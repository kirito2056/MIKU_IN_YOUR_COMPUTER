import { useRef, useEffect, useState } from 'react'
import { useFrame, useLoader, useThree } from '@react-three/fiber'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { VRMLoaderPlugin, VRMExpressionPresetName, VRMHumanBoneName } from '@pixiv/three-vrm'
import { VRMAnimationLoaderPlugin, createVRMAnimationClip } from '@pixiv/three-vrm-animation'
import type { VRM, VRMPose } from '@pixiv/three-vrm'
import * as THREE from 'three'

const VRM_PATH = '/models/miku_v1.vrm'
const VRMA_IDLE_PATH = '/motions/VRMA_01.vrma'
const VRMA_ENABLED = true // miku_v1.vrm과 VRoid VRMA 호환 이슈

/** T-pose → 자연스러운 A-pose (팔을 양옆으로 자연스럽게 내림) */
function createNaturalStandPose(): Partial<VRMPose> {
  const q = (x: number, y: number, z: number, angle: number) =>
    new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(x, y, z), angle).toArray() as [number, number, number, number]

  return {
    [VRMHumanBoneName.LeftUpperArm]: { rotation: q(0, 0, 1, -Math.PI / 2) },
    [VRMHumanBoneName.RightUpperArm]: { rotation: q(0, 0, 1, Math.PI / 2) },
  }
}

const NATURAL_STAND_POSE = createNaturalStandPose()

class VRMGLTFLoader extends GLTFLoader {
  constructor() {
    super()
    this.register((parser) => new VRMLoaderPlugin(parser))
  }
}

class VRMAGLTFLoader extends GLTFLoader {
  constructor() {
    super()
    this.register((parser) => new VRMAnimationLoaderPlugin(parser))
  }
}

/** 마우스 위치를 3D 공간의 LookAt 타겟으로 변환 */
function useLookAtTarget() {
  const { camera, size, gl } = useThree()
  const [mouse, setMouse] = useState<{ x: number; y: number } | null>(null)
  const targetRef = useRef(new THREE.Object3D())
  const raycaster = useRef(new THREE.Raycaster())
  const plane = useRef(new THREE.Plane(new THREE.Vector3(0, 0, -1), 0))
  const intersect = useRef(new THREE.Vector3())

  useEffect(() => {
    const canvas = gl.domElement
    const onMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect()
      const x = e.clientX - rect.left
      const y = e.clientY - rect.top
      if (x >= 0 && x <= rect.width && y >= 0 && y <= rect.height) {
        setMouse({ x, y })
      }
    }
    window.addEventListener('pointermove', onMove)
    return () => window.removeEventListener('pointermove', onMove)
  }, [gl.domElement])

  useFrame(() => {
    if (!size?.width || !size?.height) return
    const { x: px, y: py } = mouse ?? { x: size.width / 2, y: size.height / 2 }
    const ndcX = (px / size.width) * 2 - 1
    const ndcY = -(py / size.height) * 2 + 1
    raycaster.current.setFromCamera(new THREE.Vector2(ndcX, ndcY), camera)
    if (raycaster.current.ray.intersectPlane(plane.current, intersect.current)) {
      targetRef.current.position.copy(intersect.current)
    }
  })

  return targetRef.current
}

/** 자연스러운 서있기 - 호흡 + 미세한 무게 이동 */
function useIdleBreathing(vrm: VRM | null, active: boolean) {
  const time = useRef(0)
  const tempQuat = useRef(new THREE.Quaternion())
  const deltaQuat = useRef(new THREE.Quaternion())
  const basePose = useRef<VRMPose | null>(null)

  useFrame((_, delta) => {
    if (!active || !vrm?.humanoid) return
    const humanoid = vrm.humanoid

    if (!basePose.current) {
      basePose.current = { ...humanoid.getNormalizedPose(), ...NATURAL_STAND_POSE }
    }

    time.current += delta
    const t = time.current
    const breath = Math.sin(t * 1.2) * 0.015
    const sway = Math.sin(t * 0.7) * 0.008

    const pose: VRMPose = { ...basePose.current }

    const applyBreath = (boneName: string) => {
      const base = basePose.current?.[boneName as keyof VRMPose]?.rotation
      const baseQ = base ? new THREE.Quaternion().fromArray(base) : new THREE.Quaternion()
      deltaQuat.current.setFromEuler(new THREE.Euler(breath, 0, 0))
      tempQuat.current.copy(baseQ).multiply(deltaQuat.current)
      pose[boneName as keyof VRMPose] = {
        ...pose[boneName as keyof VRMPose],
        rotation: tempQuat.current.toArray() as [number, number, number, number],
      }
    }

    const applySway = (boneName: string) => {
      const base = basePose.current?.[boneName as keyof VRMPose]?.rotation
      const baseQ = base ? new THREE.Quaternion().fromArray(base) : new THREE.Quaternion()
      deltaQuat.current.setFromEuler(new THREE.Euler(0, sway, 0))
      tempQuat.current.copy(baseQ).multiply(deltaQuat.current)
      pose[boneName as keyof VRMPose] = {
        ...pose[boneName as keyof VRMPose],
        rotation: tempQuat.current.toArray() as [number, number, number, number],
      }
    }

    if (humanoid.getNormalizedBone(VRMHumanBoneName.Spine)) applyBreath(VRMHumanBoneName.Spine)
    if (humanoid.getNormalizedBone(VRMHumanBoneName.Chest)) applyBreath(VRMHumanBoneName.Chest)
    if (humanoid.getNormalizedBone(VRMHumanBoneName.UpperChest)) applyBreath(VRMHumanBoneName.UpperChest)
    if (humanoid.getNormalizedBone(VRMHumanBoneName.Hips)) applySway(VRMHumanBoneName.Hips)

    humanoid.setNormalizedPose(pose)
  })
}

/** Idle 깜빡임 - 주기적으로 blink 표현 적용 */
function useIdleBlink(vrm: VRM | null) {
  const blinkAccum = useRef(0)
  const isBlinking = useRef(false)

  useFrame((_, delta) => {
    if (!vrm?.expressionManager) return
    const em = vrm.expressionManager

    if (isBlinking.current) {
      const current = em.getValue(VRMExpressionPresetName.Blink) ?? 0
      if (current >= 1) {
        isBlinking.current = false
        blinkAccum.current = 0
      } else {
        em.setValue(VRMExpressionPresetName.Blink, Math.min(1, current + delta * 8))
      }
    } else {
      blinkAccum.current += delta
      if (blinkAccum.current > 2.5 + Math.random() * 2) {
        isBlinking.current = true
      } else {
        const current = em.getValue(VRMExpressionPresetName.Blink) ?? 0
        if (current > 0) {
          em.setValue(VRMExpressionPresetName.Blink, Math.max(0, current - delta * 10))
        }
      }
    }
  })
}

export function MikuModel() {
  const vrmRef = useRef<VRM | null>(null)
  const mixerRef = useRef<THREE.AnimationMixer | null>(null)
  const [vrmaActive, setVrmaActive] = useState(false)
  const lookAtTarget = useLookAtTarget()

  const gltf = useLoader(VRMGLTFLoader, VRM_PATH) as {
    scene: THREE.Group
    userData: { vrm?: VRM }
  }

  const vrm = gltf.userData?.vrm
  if (vrm) {
    console.log('[MikuModel] VRM 로드됨')
    vrmRef.current = vrm
    if (vrm.lookAt) {
      vrm.lookAt.target = lookAtTarget
      vrm.lookAt.autoUpdate = true
    }
  }

  useEffect(() => {
    if (!VRMA_ENABLED || !vrm?.humanoid) {
      console.log('[VRMA] skip:', { VRMA_ENABLED, hasHumanoid: !!vrm?.humanoid })
      return
    }
    console.log('[VRMA] 로드 시작:', VRMA_IDLE_PATH)
    const vrmaLoader = new VRMAGLTFLoader()
    vrmaLoader.load(
      VRMA_IDLE_PATH,
      (vrmaGltf) => {
        console.log('[VRMA] 로드 완료:', vrmaGltf)
        const animations = vrmaGltf.userData?.vrmAnimations
        console.log('[VRMA] animations:', animations?.length, animations)
        if (!animations?.length || !vrmRef.current) {
          console.warn('[VRMA] 재생 불가:', { animationsLen: animations?.length, hasVrm: !!vrmRef.current })
          return
        }
        try {
          const vrmAnimation = animations[0]
          const clip = createVRMAnimationClip(vrmAnimation, vrmRef.current as never)
          console.log('[VRMA] clip 생성:', clip.duration, 'sec')
          const mixer = new THREE.AnimationMixer(vrmRef.current.scene)
          const action = mixer.clipAction(clip)
          action.setLoop(THREE.LoopRepeat, Infinity)
          action.play()
          mixerRef.current = mixer
          setVrmaActive(true)
          console.log('[VRMA] 재생 시작')
        } catch (e) {
          console.error('[VRMA] 재생 에러:', e)
          setVrmaActive(false)
        }
      },
      (progress) => {
        if (progress?.lengthComputable && typeof progress.total === 'number') {
          console.log('[VRMA] 로딩:', Math.round((progress.loaded / progress.total) * 100) + '%')
        }
      },
      (err) => {
        console.error('[VRMA] 로드 실패:', err)
        setVrmaActive(false)
      }
    )
  }, [vrm])

  useEffect(() => {
    if (!vrmaActive && vrm?.humanoid) {
      const pose = { ...vrm.humanoid.getNormalizedPose(), ...NATURAL_STAND_POSE }
      vrm.humanoid.setNormalizedPose(pose)
    }
  }, [vrm, vrmaActive])

  useIdleBlink(vrm ?? null)
  useIdleBreathing(vrm ?? null, !vrmaActive)

  useFrame((_, delta) => {
    try {
      if (vrmRef.current) vrmRef.current.update(delta)
      if (mixerRef.current) mixerRef.current.update(delta)
    } catch (e) {
      console.error('[MikuModel] useFrame 에러:', e)
      mixerRef.current = null
      requestAnimationFrame(() => setVrmaActive(false))
    }
  })

  return gltf.scene ? <primitive object={gltf.scene} /> : null
}

useLoader.preload(VRMGLTFLoader, VRM_PATH)
