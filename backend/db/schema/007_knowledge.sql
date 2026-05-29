-- Knowledge Graph (Facts) — docs/backend/db.md §2-B

CREATE TABLE IF NOT EXISTS knowledge_facts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject         TEXT NOT NULL,
    predicate       TEXT NOT NULL,
    object          TEXT NOT NULL,
    confidence      REAL NOT NULL DEFAULT 0.8 CHECK (confidence >= 0 AND confidence <= 1),
    source_turn_id  UUID REFERENCES conversation_turns(id) ON DELETE SET NULL,
    embedding       embedding_vec,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deprecated_at   TIMESTAMPTZ
);

COMMENT ON TABLE knowledge_facts IS 'User-Likes-MintChocolate 형태의 사실 트리플 + 선택적 벡터 검색';

CREATE INDEX IF NOT EXISTS idx_knowledge_facts_user_active
    ON knowledge_facts (user_id, is_active)
    WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_knowledge_facts_spo
    ON knowledge_facts (user_id, subject, predicate);
