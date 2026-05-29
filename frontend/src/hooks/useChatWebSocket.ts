import { useCallback, useEffect, useRef, useState } from 'react'
import {
  BACKEND_WS_URL,
  WS_RECONNECT_INTERVAL_MS,
  WS_RECONNECT_MAX,
} from '../config'
import { playOggFromBase64Chunks } from '../utils/playAudio'

export type ConnectionStatus =
  | 'connecting'
  | 'connected'
  | 'disconnected'
  | 'error'

type ServerMessage =
  | { type: 'response'; message: string }
  | { type: 'error'; message: string }
  | { type: 'pong' }
  | { type: 'audio_start'; format: string }
  | { type: 'audio_chunk'; data: string }
  | { type: 'audio_end' }
  | { type: 'tts_error'; message: string }

type SendOptions = {
  withTts?: boolean
}

export function useChatWebSocket() {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttempts = useRef(0)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pendingResolve = useRef<((text: string) => void) | null>(null)
  const pendingReject = useRef<((err: Error) => void) | null>(null)
  const audioChunksRef = useRef<string[]>([])
  const unmounted = useRef(false)

  const [status, setStatus] = useState<ConnectionStatus>('connecting')
  const [statusMessage, setStatusMessage] = useState('연결 중…')
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [ttsError, setTtsError] = useState<string | null>(null)

  const clearPending = useCallback((err?: Error) => {
    if (err && pendingReject.current) {
      pendingReject.current(err)
    }
    pendingResolve.current = null
    pendingReject.current = null
  }, [])

  const finishAudio = useCallback(async () => {
    const chunks = audioChunksRef.current
    audioChunksRef.current = []
    if (chunks.length === 0) {
      setIsSpeaking(false)
      return
    }
    try {
      await playOggFromBase64Chunks(chunks)
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : '오디오 재생에 실패했습니다.'
      setTtsError(msg)
    } finally {
      setIsSpeaking(false)
    }
  }, [])

  const connect = useCallback(() => {
    if (unmounted.current) return

    if (wsRef.current?.readyState === WebSocket.OPEN) return

    setStatus('connecting')
    setStatusMessage('연결 중…')

    const ws = new WebSocket(BACKEND_WS_URL)
    wsRef.current = ws

    ws.onopen = () => {
      if (unmounted.current) return
      reconnectAttempts.current = 0
      setStatus('connected')
      setStatusMessage('연결됨')
    }

    ws.onmessage = (event) => {
      if (unmounted.current) return
      let data: ServerMessage
      try {
        data = JSON.parse(event.data)
      } catch {
        return
      }

      if (data.type === 'pong') return

      if (data.type === 'response' && pendingResolve.current) {
        pendingResolve.current(data.message)
        pendingResolve.current = null
        pendingReject.current = null
        return
      }

      if (data.type === 'audio_start') {
        audioChunksRef.current = []
        setIsSpeaking(true)
        setTtsError(null)
        return
      }

      if (data.type === 'audio_chunk') {
        audioChunksRef.current.push(data.data)
        return
      }

      if (data.type === 'audio_end') {
        void finishAudio()
        return
      }

      if (data.type === 'tts_error') {
        setIsSpeaking(false)
        setTtsError(data.message)
        return
      }

      if (data.type === 'error') {
        setStatus('error')
        setStatusMessage(data.message)
        if (pendingReject.current) {
          pendingReject.current(new Error(data.message))
          pendingResolve.current = null
          pendingReject.current = null
        }
      }
    }

    ws.onclose = () => {
      if (unmounted.current) return
      wsRef.current = null
      clearPending(new Error('연결이 끊어졌습니다.'))
      setIsSpeaking(false)
      audioChunksRef.current = []

      if (reconnectAttempts.current >= WS_RECONNECT_MAX) {
        setStatus('error')
        setStatusMessage('재연결 실패 (최대 횟수 초과)')
        return
      }

      reconnectAttempts.current += 1
      setStatus('disconnected')
      setStatusMessage(
        `재연결 중… (${reconnectAttempts.current}/${WS_RECONNECT_MAX})`,
      )

      reconnectTimer.current = setTimeout(() => {
        connect()
      }, WS_RECONNECT_INTERVAL_MS)
    }

    ws.onerror = () => {
      if (unmounted.current) return
      setStatus('error')
      setStatusMessage('연결 오류')
    }
  }, [clearPending, finishAudio])

  useEffect(() => {
    unmounted.current = false
    connect()

    return () => {
      unmounted.current = true
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current)
      }
      clearPending(new Error('연결 종료'))
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [connect, clearPending])

  const sendMessage = useCallback(
    (message: string, options?: SendOptions): Promise<string> => {
      const ws = wsRef.current
      if (!ws || ws.readyState !== WebSocket.OPEN) {
        return Promise.reject(new Error('백엔드에 연결되어 있지 않습니다.'))
      }

      if (pendingResolve.current) {
        return Promise.reject(new Error('이전 메시지 처리 중입니다.'))
      }

      setTtsError(null)

      return new Promise((resolve, reject) => {
        pendingResolve.current = resolve
        pendingReject.current = reject
        ws.send(
          JSON.stringify({
            type: 'chat',
            message,
            with_tts: options?.withTts ?? false,
          }),
        )
      })
    },
    [],
  )

  return { status, statusMessage, sendMessage, isSpeaking, ttsError }
}
