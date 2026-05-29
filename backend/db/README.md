# MIKU Database (PostgreSQL 17 + pgvector)

Phase 2 메모리 계층(L1/L2/L3)의 **L2 중기 기억** 저장소입니다.  
설계 근거: [docs/backend/db.md](../../docs/backend/db.md), [docs/planning/06_hardware_memory_strategy.md](../../docs/planning/06_hardware_memory_strategy.md)

## 메모리 계층 ↔ 테이블

| 계층 | 저장 | 테이블 | 비고 |
|------|------|--------|------|
| **L1** | RAM (+ spill) | `short_term_turns` | 최근 ~1h, TTL. RAM은 백엔드 세션 |
| **L2** | SSD / PostgreSQL | `conversation_turns`, `conversation_summaries`, `knowledge_facts` | pgvector RAG |
| **L3** | HDD Vault | `conversation_turns.vault_path`, `media_assets.file_path` | `vault_status=archived` |

---

## 빠른 시작 (Windows + Docker — 권장)

**Docker Desktop for Windows**로 pgvector 포함 PostgreSQL 17을 띄웁니다.  
네이티브 PostgreSQL 설치·Stack Builder 없이 동일 스키마를 쓸 수 있습니다.

### 사전 준비

1. [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/) 설치
2. Docker Desktop **실행** (트레이 아이콘 Running 상태)
3. PowerShell에서 `docker compose version` 확인

### 1. DB 컨테이너 기동

프로젝트 루트:

```powershell
docker compose up -d postgres
docker compose ps
```

- 이미지: `pgvector/pgvector:pg17`
- 포트: `localhost:5432`
- 계정: `miku` / `miku`, DB: `miku`
- **최초 기동 시** `backend/db/schema/*.sql`이 자동 실행됩니다 (`docker-entrypoint-initdb.d`)

### 2. 스키마 적용 / 재적용 (호스트 Python)

스키마를 수정했거나 볼륨을 지운 뒤 다시 맞출 때:

```powershell
cd backend
pip install psycopg2-binary

# backend\.env (호스트 → localhost)
# DATABASE_URL=postgresql://miku:miku@localhost:5432/miku

python db/apply_schema.py --dry-run
python db/apply_schema.py
```

한 번에:

```powershell
python scripts/dev_db.py
python scripts/dev_db.py --reset   # DB volume 초기화
```

### 3. 연결 확인

```powershell
docker compose exec postgres psql -U miku -d miku -c "\dt"
```

### 4. 백엔드 + DB 함께 (Docker)

```powershell
docker compose up -d
```

컨테이너 내부 백엔드는 `DATABASE_URL=postgresql://miku:miku@postgres:5432/miku` 로 DB에 연결합니다.

### Windows 경로 (기획 · Vault 파일)

| 용도 | 경로 |
|------|------|
| Docker DB 볼륨 | Docker volume `miku_pgdata` (WSL2 디스크 내부) |
| HDD Vault (파일) | `D:\MIKU_DATA\vault\` |
| 모델 | `D:\MIKU_DATA\models\` |

> LLM/GPU 작업은 **호스트 Windows**에서 그대로 실행하고, **DB만 Docker**에 두는 구성을 권장합니다.

### DB 초기화 (데이터 전부 삭제)

```powershell
docker compose down -v
python scripts/dev_db.py
```

---

## 대안: Windows 네이티브 PostgreSQL

Docker Desktop을 쓰지 않을 때만 [PostgreSQL 17 Windows 설치](https://www.postgresql.org/download/windows/) + Stack Builder pgvector 후, 동일하게 `python db/apply_schema.py` 실행.

---

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
| `010_indexes.sql` | HNSW (cosine) |
| `011_seed_dev.sql` | dev Master 사용자 |

## 벡터 검색

- 거리: **cosine** (`vector_cosine_ops`)
- 임베딩 차원: **768** (`embedding_vec` domain)

## RAG 검색 예시

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

## 다음 단계 (미구현)

- [ ] `services/memory_service.py` — L1 RAM + DB 연동
- [ ] 임베딩 파이프라인 (Gemma embedding)
- [ ] L1→L2 Context Sliding / 수면 모드 L2→L3 이관
