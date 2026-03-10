import { useRef, useEffect, useState } from 'react'
import { useFrame, useLoader, useThree } from '@react-three/fiber'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { VRMLoaderPlugin, VRMExpressionPresetName } from '@pixiv/three-vrm'
import type { VRM } from '@pixiv/three-vrm'
import * as THREE from 'three'

const VRM_PATH = '/models/miku_v1.vrm'

class VRMGLTFLoader extends GLTFLoader {
  constructor() {
    super()
    this.register((parser) => new VRMLoaderPlugin(parser))
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
    if (size.width === 0 || size.height === 0) return
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
  const lookAtTarget = useLookAtTarget()

  const gltf = useLoader(VRMGLTFLoader, VRM_PATH) as {
    scene: THREE.Group
    userData: { vrm?: VRM }
  }

  const vrm = gltf.userData?.vrm
  if (vrm) {
    vrmRef.current = vrm
    if (vrm.lookAt) {
      vrm.lookAt.target = lookAtTarget
      vrm.lookAt.autoUpdate = true
    }
  }

  useIdleBlink(vrm ?? null)

  useFrame((_, delta) => {
    if (vrmRef.current) {
      vrmRef.current.update(delta)
    }
  })

  return gltf.scene ? <primitive object={gltf.scene} /> : null
}

useLoader.preload(VRMGLTFLoader, VRM_PATH)
