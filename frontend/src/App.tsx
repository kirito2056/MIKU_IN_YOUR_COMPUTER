import { Suspense, useState } from 'react'
import { Scene3D } from './components/Scene3D'
import { ChatPanel } from './components/ChatPanel'

function ModelLoadingFallback() {
  return (
    <div style={{
      width: '100%',
      height: '100%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      color: '#00ffff',
      fontSize: '18px',
      backgroundColor: 'rgba(0, 0, 0, 0.3)',
    }}>
      Miku 로딩 중...
    </div>
  )
}

function App() {
  const [currentMotion, setCurrentMotion] = useState<string | null>(null)

  return (
    <div style={{
      position: 'relative',
      width: '100vw',
      height: '100vh',
      overflow: 'hidden',
    }}>
      {/* 3D VRM 모델 영역 */}
      <div style={{
        position: 'absolute',
        left: 0,
        bottom: 0,
        width: '960px',
        height: '1440px',
        boxSizing: 'border-box',
        pointerEvents: 'auto',
      }}>
        <Suspense fallback={<ModelLoadingFallback />}>
          <Scene3D onMotionSelect={setCurrentMotion} />
        </Suspense>
      </div>

      <ChatPanel currentMotion={currentMotion} />
    </div>
  )
}

export default App
