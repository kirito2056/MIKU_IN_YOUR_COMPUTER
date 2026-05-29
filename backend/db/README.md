# MIKU Database (PostgreSQL 17 + pgvector)

Phase 2 메모리 계층(L1/L2/L3)의 **L2 중기 기억** 저장소입니다.  
설계 근거: [docs/backend/db.md](../../docs/backend/db.md), [docs/planning/06_hardware_memory_strategy.md](../../docs/planning/06_hardware_memory_strategy.md)

## 메모리 계층 ↔ 테이블

| 계층 | 저장 | 테이블 | 비고 |
|------|------|--------|------|
| **L1** | RAM (+ spill) | `short_term_turns` | 최근 ~1h, TTL. RAM은 백엔드 세션 |
| **L2** | SSD / PostgreSQL | `conversation_turns`, `conversation_summaries`, `knowledge_facts` | pgvector RAG |
| **L3** | HDD Vault | `conversation_turns.vault_path`, `media_assets.file_path` | `vault_status=archived` |

## 빠른 시작 (Docker)

```powershell
# 프로젝트 루트
docker compose up -d postgres

cd backend
pip install psycopg2-binary
copy db\.env.example .env   # DATABASE_URL 확인
python db/apply_schema.py
python db/apply_schema.py --dry-run   # 적용 전 확인
```

개발용 시드 (기본 Master 사용자):

```powershell
python db/apply_schema.py   # 001~010 적용 후
psql %DATABASE_URL% -f db/schema/011_seed_dev.sql
```

## 스키마 파일 순서

| 파일 | 내용 |
|------|------|
| `001_extensions.sql` | vector, pgcrypto, schema_migrations |
| `002_types.sql` | speaker_role, memory_tier, embedding_vec(768) |
| `003_identity.sql` | users, growth_stats, wallet_items |
| `004_sessions.sql` | chat_sessions |
| `005_short_term.sql` | short_term_turns (L1 spill) |
| `006_conversations.sql` | conversation_turns, conversation_summaries |
| `007_knowledge.sql` | knowledge_facts |
| `008_diary_media.sql` | diary_entries, media_assets |
| `009_system.sql` | system_logs, usage_patterns |
| `010_indexes.sql` | HNSW (cosine). IVFFlat은 데이터 적재 후 선택 |
| `011_seed_dev.sql` | (선택) 로컬 dev 기본 user |

## 벡터 검색

- 거리: **cosine** (`vector_cosine_ops`)
- 임베딩 차원: **768** (`embedding_vec` domain)
- 1만 건 이후 HNSW 전환: [vector_search_optimization.md](../../docs/backend/vector_search_optimization.md)

## RAG 검색 예시 (임베딩 입력 후)

```sql
SELECT id, speaker, content,
       1 - (embedding <=> :query_vec) AS similarity
FROM conversation_turns
WHERE user_id = :uid
  AND embedding IS NOT NULL
  AND vault_status = 'active'
ORDER BY embedding <=> :query_vec
LIMIT 5;
```

## 경로 (기획)

- SSD DB: `C:/MIKU_DATA/fast_memory/` (또는 Docker volume)
- HDD Vault: `D:/MIKU_DATA/vault/` — 파일 본문, DB에는 경로·메타만

## 다음 단계 (미구현)

- [ ] `services/memory_service.py` — L1 RAM + DB 연동
- [ ] 임베딩 파이프라인 (Gemma embedding)
- [ ] L1→L2 Context Sliding / 수면 모드 L2→L3 이관
