-- Tier 1 (Hot): 사용자·성장·인벤토리 — docs/backend/db.md §1

CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    display_name    TEXT NOT NULL DEFAULT 'Master',
    device_id       TEXT UNIQUE,
    locale          TEXT NOT NULL DEFAULT 'ko',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE users IS '로컬 단일 사용자 프로필 (device_id = MAC/UUID)';

CREATE TABLE IF NOT EXISTS growth_stats (
    user_id             UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    intimacy            INTEGER NOT NULL DEFAULT 0 CHECK (intimacy >= 0),
    level               INTEGER NOT NULL DEFAULT 1 CHECK (level >= 1),
    unlocked_features   JSONB NOT NULL DEFAULT '[]'::jsonb,
    hidden_stats        JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE growth_stats IS '친밀도·레벨·Natural Growth 해금 (스탯창 없음)';

CREATE TABLE IF NOT EXISTS wallet_items (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    item_key    TEXT NOT NULL,
    quantity    INTEGER NOT NULL DEFAULT 1 CHECK (quantity >= 0),
    metadata    JSONB NOT NULL DEFAULT '{}'::jsonb,
    acquired_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, item_key)
);

COMMENT ON TABLE wallet_items IS '보유 아이템·코인 (Wallet/Inventory)';

CREATE INDEX IF NOT EXISTS idx_wallet_items_user ON wallet_items (user_id);
