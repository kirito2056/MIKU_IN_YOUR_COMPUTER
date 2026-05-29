-- MIKU IN YOUR COMPUTER — PostgreSQL 17+ / pgvector
-- docs/backend/db.md, docs/planning/06_hardware_memory_strategy.md

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version     TEXT PRIMARY KEY,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE schema_migrations IS '적용된 schema/*.sql 파일명 추적';
