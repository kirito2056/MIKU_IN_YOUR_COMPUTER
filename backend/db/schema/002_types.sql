-- 공통 ENUM (스키마 변경 최소화를 위해 타입 분리)

DO $$ BEGIN
    CREATE TYPE speaker_role AS ENUM ('user', 'miku', 'system');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE memory_tier AS ENUM ('short', 'mid', 'long');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE vault_status AS ENUM ('active', 'archived');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- Gemma 4 텍스트 임베딩 차원 (db.md: vector(768). 모델 변경 시 마이그레이션 필요)
DO $$ BEGIN
    PERFORM 1 FROM pg_type WHERE typname = 'embedding_vec';
    IF NOT FOUND THEN
        CREATE DOMAIN embedding_vec AS vector(768);
    END IF;
END $$;

COMMENT ON DOMAIN embedding_vec IS 'Gemma 4 계열 텍스트 임베딩 (768d). 변경 시 ALTER DOMAIN 불가 → 새 domain + migration';
