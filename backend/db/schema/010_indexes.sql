-- pgvector 인덱스 — docs/backend/vector_search_optimization.md §2.3
-- HNSW: 빈 테이블에서도 생성 가능 (로컬 dev). 데이터 1만+ 건이면 파라미터 튜닝.

CREATE INDEX IF NOT EXISTS conversation_turns_embedding_hnsw_idx
    ON conversation_turns
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64)
    WHERE embedding IS NOT NULL;

CREATE INDEX IF NOT EXISTS conversation_summaries_embedding_hnsw_idx
    ON conversation_summaries
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64)
    WHERE embedding IS NOT NULL;

CREATE INDEX IF NOT EXISTS knowledge_facts_embedding_hnsw_idx
    ON knowledge_facts
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64)
    WHERE embedding IS NOT NULL;

-- IVFFlat (소규모·메모리 절약) 대안 — 데이터 적재 후 수동:
-- CREATE INDEX ... USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
