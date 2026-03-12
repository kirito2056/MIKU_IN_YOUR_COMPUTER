import { Suspense, useState } from 'react'
import { Scene3D } from './components/Scene3D'

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
  const [message] = useState('Hello, Miku is coming!');
  console.log('[App] render');

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
          <Scene3D />
        </Suspense>
      </div>

      {/* 대화창 */}
      <div style={{
        position: 'absolute',
        bottom: '40px',
        right: '40px',
        backgroundColor: 'rgba(0, 0, 0, 0.7)',
        color: 'white',
        padding: '25px',
        borderRadius: '15px',
        width: '400px',
        minHeight: '120px',
        fontFamily: 'sans-serif',
        pointerEvents: 'auto', // 이 박스는 클릭 가능하게
        zIndex: 10,
      }}>
        <p style={{ margin: '0 0 10px 0', fontSize: '24px', color: '#00ffff', fontWeight: 'bold' }}>Miku</p>
        <p style={{ margin: 0, fontSize: '20px', lineHeight: '1.5' }}>{message}</p>
      </div>
    </div>
  )
}

export default App
