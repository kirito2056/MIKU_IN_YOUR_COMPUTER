import { useRef } from 'react'
import { useFrame, useLoader } from '@react-three/fiber'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { VRMLoaderPlugin } from '@pixiv/three-vrm'
import type { VRM } from '@pixiv/three-vrm'

const VRM_PATH = '/models/miku_v1.vrm'

class VRMGLTFLoader extends GLTFLoader {
  constructor() {
    super()
    this.register((parser) => new VRMLoaderPlugin(parser))
  }
}

export function MikuModel() {
  const vrmRef = useRef<VRM | null>(null)

  const gltf = useLoader(VRMGLTFLoader, VRM_PATH) as {
    scene: THREE.Group
    userData: { vrm?: VRM }
  }

  const vrm = gltf.userData?.vrm
  if (vrm) {
    vrmRef.current = vrm
  }

  useFrame((_, delta) => {
    if (vrmRef.current) {
      vrmRef.current.update(delta)
    }
  })

  return gltf.scene ? <primitive object={gltf.scene} /> : null
}

useLoader.preload(VRMGLTFLoader, VRM_PATH)
