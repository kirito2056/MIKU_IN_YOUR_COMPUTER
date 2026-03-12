import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

console.log('[main] 앱 시작')
window.addEventListener('error', (e) => console.error('[전역 에러]', e))
window.addEventListener('unhandledrejection', (e) => console.error('[전역 Promise 에러]', e.reason))
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
