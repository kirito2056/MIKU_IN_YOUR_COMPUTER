import { Canvas } from '@react-three/fiber'
import { MikuModel } from './MikuModel'

export function Scene3D() {
  return (
    <Canvas
      camera={{ position: [0, 0.25, 2.2], fov: 35 }}
      gl={{ alpha: true, antialias: true }}
      style={{ width: '100%', height: '100%', background: 'transparent' }}
    >
      <ambientLight intensity={0.8} />
        <directionalLight position={[2, 4, 3]} intensity={1.2} castShadow />
        <directionalLight position={[-2, 2, 2]} intensity={0.5} />
        <group position={[0, -0.55, 0]} scale={0.5} rotation={[0, Math.PI, 0]}>
          <MikuModel />
        </group>
    </Canvas>
  )
}
