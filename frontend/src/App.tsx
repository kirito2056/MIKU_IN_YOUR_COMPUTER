import { useState, useEffect } from 'react'

function App() {
  const [message, setMessage] = useState('Hello, Miku is coming!');

  return (
    <div style={{
      position: 'relative',
      width: '100vw',
      height: '100vh',
      overflow: 'hidden',
    }}>
      {/* 3D 모델이 들어갈 자리 (임시 박스) */}
      <div style={{
        position: 'absolute',
        right: 0,
        bottom: 0,
        width: '960px',
        height: '1440px',
        backgroundColor: 'rgba(0, 255, 255, 0.2)',
        border: '2px dashed #00ffff',
        boxSizing: 'border-box',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        color: '#00ffff',
        fontWeight: 'bold',
        pointerEvents: 'auto', // 이 박스는 클릭 가능하게
      }}>
        Miku 3D Model Area
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
