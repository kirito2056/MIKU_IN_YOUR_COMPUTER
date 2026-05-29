-- L1 단기 기억 spillover — RAM 10~20턴 + 최근 ~1시간 (db.md ShortTermMemory)

CREATE TABLE IF NOT EXISTS short_term_turns (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id      UUID REFERENCES chat_sessions(id) ON DELETE SET NULL,
    turn_index      INTEGER NOT NULL CHECK (turn_index >= 0),
    speaker         speaker_role NOT NULL,
    content         TEXT NOT NULL,
    emotion         JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '1 hour')
);

COMMENT ON TABLE short_term_turns IS 'L1: 최근 대화 턴. RAM 미러 + 1h TTL. L2 승격 전 버퍼';

CREATE INDEX IF NOT EXISTS idx_short_term_user_created
    ON short_term_turns (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_short_term_session_turn
    ON short_term_turns (session_id, turn_index);

CREATE INDEX IF NOT EXISTS idx_short_term_expires
    ON short_term_turns (expires_at)
    WHERE expires_at IS NOT NULL;
