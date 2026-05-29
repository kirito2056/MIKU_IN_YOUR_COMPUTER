-- Tier 2 Cold (HDD Vault 메타) — docs/backend/db.md §1

CREATE TABLE IF NOT EXISTS diary_entries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    entry_date      DATE NOT NULL,
    content         TEXT NOT NULL,
    embedding       embedding_vec,
    vault_path      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, entry_date)
);

COMMENT ON TABLE diary_entries IS '미쿠 일기 (Backlog 기능, 스키마만 선행)';

CREATE TABLE IF NOT EXISTS media_assets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    media_type      TEXT NOT NULL,
    file_path       TEXT NOT NULL,
    title           TEXT,
    embedding       embedding_vec,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE media_assets IS '생성 그림·음악·녹음 — 실제 파일은 D:/MIKU_DATA/vault/';

CREATE INDEX IF NOT EXISTS idx_media_assets_user_type
    ON media_assets (user_id, media_type, created_at DESC);
