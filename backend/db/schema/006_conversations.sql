-- L2/L3 대화 로그 + 벡터 (RAG). docs/backend/db.md §2-A

CREATE TABLE IF NOT EXISTS conversation_turns (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id      UUID REFERENCES chat_sessions(id) ON DELETE SET NULL,
    short_term_id   UUID REFERENCES short_term_turns(id) ON DELETE SET NULL,
    speaker         speaker_role NOT NULL,
    content         TEXT NOT NULL,
    embedding       embedding_vec,
    emotion         JSONB NOT NULL DEFAULT '{}'::jsonb,
    memory_tier     memory_tier NOT NULL DEFAULT 'mid',
    vault_status    vault_status NOT NULL DEFAULT 'active',
    archived_at     TIMESTAMPTZ,
    vault_path      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb
);

COMMENT ON TABLE conversation_turns IS 'L2(중기, SSD/pgvector) / L3(장기, Vault 이관) 대화. embedding NULL=미임베딩';
COMMENT ON COLUMN conversation_turns.vault_path IS 'L3 HDD 아카이브 파일 경로 (예: D:/MIKU_DATA/vault/...)';

CREATE INDEX IF NOT EXISTS idx_conversation_user_created
    ON conversation_turns (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_conversation_session
    ON conversation_turns (session_id, created_at);

CREATE INDEX IF NOT EXISTS idx_conversation_tier_active
    ON conversation_turns (memory_tier, vault_status)
    WHERE vault_status = 'active';

-- L2 요약 (Context Sliding: L1이 길어질 때 요약본을 L2에 저장)
CREATE TABLE IF NOT EXISTS conversation_summaries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id      UUID REFERENCES chat_sessions(id) ON DELETE SET NULL,
    summary_text    TEXT NOT NULL,
    embedding       embedding_vec,
    covers_from     TIMESTAMPTZ,
    covers_until    TIMESTAMPTZ,
    turn_count      INTEGER NOT NULL DEFAULT 0,
    memory_tier     memory_tier NOT NULL DEFAULT 'mid',
    vault_status    vault_status NOT NULL DEFAULT 'active',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE conversation_summaries IS 'L1→L2 슬라이딩 시 구간 요약 + RAG용 임베딩';

CREATE INDEX IF NOT EXISTS idx_conversation_summaries_user
    ON conversation_summaries (user_id, created_at DESC);
