-- 대화 세션 (WebSocket / REST 단위)

CREATE TABLE IF NOT EXISTS chat_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title           TEXT,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at        TIMESTAMPTZ,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb
);

COMMENT ON TABLE chat_sessions IS '대화 세션 단위 그룹 (L1 세션 ID와 연동 예정)';

CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_started
    ON chat_sessions (user_id, started_at DESC);
