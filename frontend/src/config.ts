const DEFAULT_WS = 'ws://localhost:8000/ws/chat'
const DEFAULT_HTTP = 'http://localhost:8000'

/** 백엔드 WebSocket URL (Vite: VITE_BACKEND_WS_URL) */
export const BACKEND_WS_URL =
  import.meta.env.VITE_BACKEND_WS_URL?.trim() || DEFAULT_WS

/** 백엔드 HTTP URL (Vite: VITE_BACKEND_HTTP_URL) */
export const BACKEND_HTTP_URL =
  import.meta.env.VITE_BACKEND_HTTP_URL?.trim() || DEFAULT_HTTP

export const WS_RECONNECT_MAX = 10
export const WS_RECONNECT_INTERVAL_MS = 5000
