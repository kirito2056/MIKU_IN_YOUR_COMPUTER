import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from 'react'
import { useChatWebSocket } from '../hooks/useChatWebSocket'

export type ChatMessage = {
  id: string
  role: 'user' | 'assistant' | 'error'
  content: string
}

type ChatPanelProps = {
  currentMotion?: string | null
}

const STATUS_COLOR: Record<string, string> = {
  connected: '#4ade80',
  connecting: '#facc15',
  disconnected: '#fb923c',
  error: '#f87171',
}

function nextId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

export function ChatPanel({ currentMotion }: ChatPanelProps) {
  const { status, statusMessage, sendMessage } = useChatWebSocket()
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: '마스터, 뭐 하고 있어? 말 걸어 봐.',
    },
  ])
  const [input, setInput] = useState('')
  const [isSending, setIsSending] = useState(false)
  const historyRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const canSend =
    status === 'connected' && !isSending && input.trim().length > 0

  useEffect(() => {
    const el = historyRef.current
    if (el) {
      el.scrollTop = el.scrollHeight
    }
  }, [messages, isSending])

  const handleSend = useCallback(async () => {
    const text = input.trim()
    if (!text || isSending || status !== 'connected') return

    setInput('')
    setIsSending(true)
    setMessages((prev) => [
      ...prev,
      { id: nextId(), role: 'user', content: text },
    ])

    try {
      const reply = await sendMessage(text)
      setMessages((prev) => [
        ...prev,
        { id: nextId(), role: 'assistant', content: reply },
      ])
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : '응답을 받지 못했습니다.'
      setMessages((prev) => [
        ...prev,
        { id: nextId(), role: 'error', content: msg },
      ])
    } finally {
      setIsSending(false)
      inputRef.current?.focus()
    }
  }, [input, isSending, sendMessage, status])

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    void handleSend()
  }

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void handleSend()
    }
  }

  return (
    <div
      style={{
        position: 'absolute',
        bottom: '40px',
        right: '40px',
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        color: 'white',
        padding: '20px',
        borderRadius: '15px',
        width: '400px',
        maxHeight: '520px',
        display: 'flex',
        flexDirection: 'column',
        fontFamily: 'sans-serif',
        pointerEvents: 'auto',
        zIndex: 10,
        boxSizing: 'border-box',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '12px',
          gap: '8px',
        }}
      >
        <p
          style={{
            margin: 0,
            fontSize: '24px',
            color: '#00ffff',
            fontWeight: 'bold',
          }}
        >
          Miku
        </p>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            flexShrink: 0,
          }}
        >
          {currentMotion && (
            <span
              style={{
                fontSize: '11px',
                color: '#aaa',
                backgroundColor: '#333',
                padding: '3px 6px',
                borderRadius: '4px',
              }}
            >
              {currentMotion}
            </span>
          )}
          <span
            title={statusMessage}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '5px',
              fontSize: '11px',
              color: '#bbb',
            }}
          >
            <span
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                backgroundColor: STATUS_COLOR[status] ?? '#888',
                flexShrink: 0,
              }}
            />
            {statusMessage}
          </span>
        </div>
      </div>

      <div
        ref={historyRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          marginBottom: '12px',
          paddingRight: '4px',
          minHeight: '120px',
          maxHeight: '320px',
        }}
      >
        {messages.map((msg) => (
          <div
            key={msg.id}
            style={{
              marginBottom: '10px',
              textAlign: msg.role === 'user' ? 'right' : 'left',
            }}
          >
            <span
              style={{
                display: 'inline-block',
                maxWidth: '92%',
                padding: '8px 12px',
                borderRadius: '12px',
                fontSize: msg.role === 'user' ? '18px' : '19px',
                lineHeight: 1.45,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                backgroundColor:
                  msg.role === 'user'
                    ? 'rgba(0, 255, 255, 0.15)'
                    : msg.role === 'error'
                      ? 'rgba(248, 113, 113, 0.2)'
                      : 'rgba(255, 255, 255, 0.08)',
                color:
                  msg.role === 'error'
                    ? '#fca5a5'
                    : msg.role === 'user'
                      ? '#e0ffff'
                      : 'white',
              }}
            >
              {msg.content}
            </span>
          </div>
        ))}
        {isSending && (
          <p style={{ margin: 0, fontSize: '16px', color: '#888' }}>
            미쿠가 생각 중…
          </p>
        )}
      </div>

      <form onSubmit={onSubmit} style={{ display: 'flex', gap: '8px' }}>
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={
            status === 'connected'
              ? '메시지 입력 (Enter 전송)'
              : '백엔드 연결 대기 중…'
          }
          disabled={status !== 'connected' || isSending}
          rows={2}
          style={{
            flex: 1,
            resize: 'none',
            borderRadius: '10px',
            border: '1px solid rgba(0, 255, 255, 0.3)',
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            color: 'white',
            padding: '10px 12px',
            fontSize: '16px',
            fontFamily: 'inherit',
            outline: 'none',
          }}
        />
        <button
          type="submit"
          disabled={!canSend}
          style={{
            alignSelf: 'flex-end',
            padding: '10px 16px',
            borderRadius: '10px',
            border: 'none',
            backgroundColor: canSend ? '#00bcd4' : '#444',
            color: canSend ? '#000' : '#888',
            fontWeight: 'bold',
            fontSize: '15px',
            cursor: canSend ? 'pointer' : 'not-allowed',
          }}
        >
          전송
        </button>
      </form>
    </div>
  )
}
