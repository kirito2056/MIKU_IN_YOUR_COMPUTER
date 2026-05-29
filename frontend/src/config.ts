const DEFAULT_WS = 'ws://localhost:8000/ws/chat'

/** 백엔드 WebSocket URL (Vite: VITE_BACKEND_WS_URL) */
export const BACKEND_WS_URL =
  import.meta.env.VITE_BACKEND_WS_URL?.trim() || DEFAULT_WS

export const WS_RECONNECT_MAX = 10
export const WS_RECONNECT_INTERVAL_MS = 5000
