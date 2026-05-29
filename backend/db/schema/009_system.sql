-- System Logs & Usage Patterns — docs/backend/db.md §2-C, §2-D

CREATE TABLE IF NOT EXISTS system_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    event_type      TEXT NOT NULL,
    severity        TEXT NOT NULL DEFAULT 'info',
    details         JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE system_logs IS 'Error, Shutdown, WakeUp 등 시스템 이벤트';

CREATE INDEX IF NOT EXISTS idx_system_logs_type_created
    ON system_logs (event_type, created_at DESC);

CREATE TABLE IF NOT EXISTS usage_patterns (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    feature         TEXT NOT NULL,
    duration_sec    INTEGER CHECK (duration_sec IS NULL OR duration_sec >= 0),
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE usage_patterns IS 'chat, vision, tts, generation, plugin_* 사용 패턴';

CREATE INDEX IF NOT EXISTS idx_usage_patterns_feature_created
    ON usage_patterns (feature, created_at DESC);
