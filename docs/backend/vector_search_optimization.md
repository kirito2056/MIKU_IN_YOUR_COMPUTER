# 벡터 검색 최적화 (Vector Search Optimization)

## 1. 개요

미쿠의 메모리 계층(L1/L2/L3)에서 중기 기억(L2)과 장기 기억(L3)의 벡터 검색 성능을 최적화하여, 대화 컨텍스트 구성 시 관련 기억을 빠르고 정확하게 검색합니다.

**참고 문서**:
- 메모리 계층 아키텍처: `docs/planning/06_hardware_memory_strategy.md`
- 데이터베이스 스키마: `docs/backend/db.md`

---

## 2. pgvector 인덱스 전략

### 2.1. 인덱스 타입 선택

PostgreSQL의 pgvector 확장은 두 가지 인덱스 타입을 제공합니다:

#### A. HNSW (Hierarchical Navigable Small World)
- **특징**: 그래프 기반 근사 최근접 이웃 검색
- **장점**:
  - 매우 빠른 검색 속도 (O(log N))
  - 높은 정확도
  - 대용량 데이터에 적합
- **단점**:
  - 인덱스 생성 시간이 오래 걸림
  - 메모리 사용량이 많음
  - 인덱스 크기가 큼
- **권장 사용**: **대용량 데이터(10만 건 이상)**, 실시간 검색이 중요한 경우

#### B. IVFFlat (Inverted File with Flat Compression)
- **특징**: 클러스터링 기반 검색
- **장점**:
  - 인덱스 생성이 빠름
  - 메모리 사용량이 적음
  - 인덱스 크기가 작음
- **단점**:
  - 검색 속도가 HNSW보다 느림
  - 정확도가 상대적으로 낮음
  - 데이터 업데이트 시 인덱스 재구축 필요
- **권장 사용**: **소규모 데이터(1만 건 이하)**, 초기 개발 단계

### 2.2. 인덱스 파라미터 설정

#### HNSW 파라미터
```sql
CREATE INDEX ON conversations 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

- **`m` (연결 수)**: 각 노드가 연결할 최대 이웃 수
  - 기본값: 16
  - 권장 범위: 16 ~ 32
  - 높을수록: 정확도 ↑, 인덱스 크기 ↑, 검색 속도 ↓
- **`ef_construction` (빌드 품질)**: 인덱스 생성 시 탐색 범위
  - 기본값: 64
  - 권장 범위: 64 ~ 128
  - 높을수록: 정확도 ↑, 인덱스 생성 시간 ↑

#### IVFFlat 파라미터
```sql
CREATE INDEX ON conversations 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

- **`lists` (클러스터 수)**: 데이터를 나눌 클러스터 개수
  - 권장값: `sqrt(행 수)` 또는 `행 수 / 1000`
  - 예: 10만 건 → 100 ~ 316

### 2.3. 권장 설정 (MIKU 프로젝트)

**초기 단계 (데이터 < 1만 건)**:
```sql
-- IVFFlat 사용 (빠른 인덱스 생성)
CREATE INDEX conversations_embedding_idx 
ON conversations 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

**안정화 단계 (데이터 > 1만 건)**:
```sql
-- HNSW로 전환 (고성능 검색)
DROP INDEX conversations_embedding_idx;

CREATE INDEX conversations_embedding_idx 
ON conversations 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

---

## 3. 검색 알고리즘 및 임계값

### 3.1. 유사도 함수 선택

pgvector는 두 가지 거리 함수를 제공합니다:

| 함수 | 공식 | 특징 | 권장 사용 |
|------|------|------|-----------|
| **Cosine Similarity** | `1 - (A·B) / (||A|| × ||B||)` | 벡터 크기 무시, 방향만 고려 | **텍스트 임베딩 (권장)** |
| **L2 Distance** | `||A - B||²` | 절대 거리 측정 | 이미지 임베딩 |

**MIKU 프로젝트**: Gemma 3 텍스트 임베딩 사용 → **Cosine Similarity 권장**

### 3.2. 검색 임계값 설정

#### A. 유사도 임계값 (Similarity Threshold)
관련 기억으로 판단할 최소 유사도 값:

```python
# 권장 임계값
SIMILARITY_THRESHOLD = 0.7  # Cosine Similarity 기준 (0.0 ~ 1.0)
```

- **0.8 이상**: 매우 관련성 높음 (강한 연관성)
- **0.7 ~ 0.8**: 관련성 있음 (일반적인 검색)
- **0.6 ~ 0.7**: 약한 관련성 (넓은 검색)
- **0.6 미만**: 관련성 낮음 (필터링)

#### B. 검색 결과 개수 (Top-K)
검색할 최대 결과 수:

```python
# 메모리 계층별 권장값
L2_SEARCH_LIMIT = 10   # 중기 기억: 최근 며칠간의 관련 기억
L3_SEARCH_LIMIT = 5    # 장기 기억: 과거의 핵심 기억만
```

#### C. 시간 기반 필터링
최근 데이터에 가중치를 부여:

```sql
-- 최근 7일 데이터 우선 검색
SELECT * FROM conversations
WHERE embedding <=> query_embedding < 1 - 0.7
  AND timestamp > NOW() - INTERVAL '7 days'
ORDER BY embedding <=> query_embedding
LIMIT 10;
```

### 3.3. 검색 쿼리 최적화

#### 기본 검색 쿼리
```sql
-- Cosine Similarity 기반 검색
SELECT 
  id,
  content,
  timestamp,
  1 - (embedding <=> %s::vector) AS similarity
FROM conversations
WHERE 1 - (embedding <=> %s::vector) > 0.7
ORDER BY embedding <=> %s::vector
LIMIT 10;
```

#### 고급 검색 (시간 가중치 적용)
```sql
-- 최근 데이터에 가중치 부여
SELECT 
  id,
  content,
  timestamp,
  1 - (embedding <=> %s::vector) AS base_similarity,
  -- 시간 가중치: 최근 7일 = 1.0, 30일 = 0.8, 그 외 = 0.6
  CASE 
    WHEN timestamp > NOW() - INTERVAL '7 days' THEN 1.0
    WHEN timestamp > NOW() - INTERVAL '30 days' THEN 0.8
    ELSE 0.6
  END AS time_weight,
  (1 - (embedding <=> %s::vector)) * 
    CASE 
      WHEN timestamp > NOW() - INTERVAL '7 days' THEN 1.0
      WHEN timestamp > NOW() - INTERVAL '30 days' THEN 0.8
      ELSE 0.6
    END AS weighted_similarity
FROM conversations
WHERE 1 - (embedding <=> %s::vector) > 0.6  -- 낮은 임계값으로 넓게 검색
ORDER BY weighted_similarity DESC
LIMIT 10;
```

---

## 4. 검색 성능 최적화

### 4.1. 캐싱 전략

#### A. 검색 결과 캐싱
동일하거나 유사한 쿼리에 대한 검색 결과를 캐싱:

```python
from functools import lru_cache
import hashlib
import numpy as np

class VectorSearchCache:
    def __init__(self, max_size=100):
        self.cache = {}
        self.max_size = max_size
    
    def _get_cache_key(self, query_embedding: np.ndarray) -> str:
        """임베딩 벡터를 해시하여 캐시 키 생성"""
        return hashlib.md5(query_embedding.tobytes()).hexdigest()
    
    def get(self, query_embedding: np.ndarray):
        """캐시에서 검색 결과 조회"""
        key = self._get_cache_key(query_embedding)
        return self.cache.get(key)
    
    def set(self, query_embedding: np.ndarray, results: list):
        """검색 결과를 캐시에 저장"""
        key = self._get_cache_key(query_embedding)
        if len(self.cache) >= self.max_size:
            # LRU: 가장 오래된 항목 제거
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        self.cache[key] = results
```

**캐시 전략**:
- **캐시 키**: 임베딩 벡터의 해시값
- **캐시 저장 위치**: RAM (L1 메모리)
- **캐시 만료**: 1시간 또는 수동 무효화
- **캐시 크기**: 최대 100개 검색 결과

#### B. 임베딩 캐싱
텍스트 → 임베딩 변환 결과를 캐싱:

```python
# 동일한 텍스트는 동일한 임베딩을 생성하므로 캐싱 가능
@lru_cache(maxsize=1000)
def get_embedding(text: str) -> np.ndarray:
    """텍스트를 임베딩으로 변환 (캐싱 적용)"""
    # Gemma 3 임베딩 모델 호출
    ...
```

### 4.2. 비동기 검색

LLM 추론과 병렬로 벡터 검색을 수행하여 전체 응답 시간을 단축:

```python
import asyncio
from typing import List, Dict

async def search_memories_async(
    query_embedding: np.ndarray,
    search_level: str = "L2"
) -> List[Dict]:
    """비동기 벡터 검색"""
    # LLM 추론과 병렬 실행 가능
    async with db_pool.acquire() as conn:
        results = await conn.fetch("""
            SELECT id, content, timestamp,
                   1 - (embedding <=> $1::vector) AS similarity
            FROM conversations
            WHERE 1 - (embedding <=> $1::vector) > 0.7
            ORDER BY embedding <=> $1::vector
            LIMIT 10
        """, query_embedding.tolist())
        return [dict(row) for row in results]

# 사용 예시
async def generate_response(user_input: str):
    # 임베딩 생성과 검색을 병렬로 실행
    query_embedding = await asyncio.to_thread(get_embedding, user_input)
    
    # LLM 추론과 벡터 검색을 병렬로 실행
    llm_task = asyncio.create_task(generate_llm_response(user_input))
    search_task = asyncio.create_task(search_memories_async(query_embedding))
    
    # 두 작업이 모두 완료될 때까지 대기
    llm_response, memories = await asyncio.gather(llm_task, search_task)
    
    # 검색된 기억을 컨텍스트에 포함
    context = build_context(user_input, memories, llm_response)
    return context
```

### 4.3. 인덱스 유지보수

#### A. 주기적 인덱스 재구축
데이터가 많이 추가되면 인덱스 성능이 저하될 수 있으므로 주기적으로 재구축:

```sql
-- 인덱스 재구축 (VACUUM ANALYZE)
VACUUM ANALYZE conversations;

-- 필요 시 인덱스 재생성
REINDEX INDEX conversations_embedding_idx;
```

**권장 주기**:
- **일일**: `VACUUM ANALYZE` (통계 정보 갱신)
- **주간**: 인덱스 상태 확인
- **월간**: 인덱스 재구축 (데이터 증가율에 따라 조정)

#### B. 인덱스 모니터링
인덱스 사용률과 성능을 모니터링:

```sql
-- 인덱스 크기 확인
SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE tablename = 'conversations';

-- 인덱스 사용 통계
SELECT 
    indexrelname,
    idx_scan,  -- 인덱스 스캔 횟수
    idx_tup_read,  -- 읽은 튜플 수
    idx_tup_fetch  -- 가져온 튜플 수
FROM pg_stat_user_indexes
WHERE tablename = 'conversations';
```

---

## 5. 메모리 계층별 검색 전략

### 5.1. L1 (RAM) - 단기 기억
- **검색 방식**: 벡터 검색 불필요 (최근 대화는 직접 접근)
- **데이터 구조**: Python List 또는 Redis
- **검색 시간**: O(1) - 인덱스 기반 직접 접근

### 5.2. L2 (SSD) - 중기 기억
- **검색 방식**: PostgreSQL + pgvector (HNSW 인덱스)
- **검색 범위**: 최근 7일 ~ 30일 데이터
- **검색 개수**: Top 10
- **유사도 임계값**: 0.7
- **검색 시간 목표**: < 50ms

### 5.3. L3 (HDD) - 장기 기억
- **검색 방식**: PostgreSQL + pgvector (HNSW 인덱스)
- **검색 범위**: 전체 아카이브 데이터
- **검색 개수**: Top 5 (핵심 기억만)
- **유사도 임계값**: 0.8 (높은 임계값으로 필터링)
- **검색 시간 목표**: < 200ms
- **검색 빈도**: 낮음 (필요 시에만)

---

## 6. 구현 예시

### 6.1. Python 구현 (FastAPI)

```python
from fastapi import FastAPI
import numpy as np
import asyncpg
from typing import List, Dict, Optional

class VectorSearchService:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.cache = VectorSearchCache(max_size=100)
    
    async def search_memories(
        self,
        query_embedding: np.ndarray,
        search_level: str = "L2",
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[Dict]:
        """벡터 검색 수행"""
        # 캐시 확인
        cached = self.cache.get(query_embedding)
        if cached:
            return cached
        
        # 시간 범위 설정
        if search_level == "L2":
            time_filter = "timestamp > NOW() - INTERVAL '30 days'"
        elif search_level == "L3":
            time_filter = "timestamp <= NOW() - INTERVAL '30 days'"
        else:
            time_filter = "TRUE"
        
        # 벡터 검색 쿼리
        query = f"""
            SELECT 
                id,
                content,
                timestamp,
                speaker,
                emotion,
                1 - (embedding <=> $1::vector) AS similarity
            FROM conversations
            WHERE {time_filter}
              AND 1 - (embedding <=> $1::vector) > $2
            ORDER BY embedding <=> $1::vector
            LIMIT $3
        """
        
        async with self.db_pool.acquire() as conn:
            results = await conn.fetch(
                query,
                query_embedding.tolist(),
                similarity_threshold,
                limit
            )
        
        # 결과 변환
        memories = [dict(row) for row in results]
        
        # 캐시 저장
        self.cache.set(query_embedding, memories)
        
        return memories
```

### 6.2. 검색 파이프라인 통합

```python
async def build_context_with_memories(
    user_input: str,
    recent_conversations: List[Dict],  # L1에서 가져온 최근 대화
    search_service: VectorSearchService
) -> str:
    """대화 컨텍스트 구성 (메모리 계층 통합)"""
    # 1. 사용자 입력을 임베딩으로 변환
    query_embedding = await get_embedding(user_input)
    
    # 2. L2 (중기 기억) 검색
    mid_term_memories = await search_service.search_memories(
        query_embedding,
        search_level="L2",
        limit=10,
        similarity_threshold=0.7
    )
    
    # 3. L3 (장기 기억) 검색 (필요 시에만)
    long_term_memories = []
    if len(mid_term_memories) < 5:  # 중기 기억이 부족하면
        long_term_memories = await search_service.search_memories(
            query_embedding,
            search_level="L3",
            limit=5,
            similarity_threshold=0.8
        )
    
    # 4. 컨텍스트 구성
    context = f"""
    [System Prompt]
    {build_system_prompt()}
    
    [Recent Conversations] (L1)
    {format_conversations(recent_conversations)}
    
    [Related Memories] (L2)
    {format_memories(mid_term_memories)}
    
    [Long-term Memories] (L3)
    {format_memories(long_term_memories)}
    
    [Current User Input]
    {user_input}
    """
    
    return context
```

---

## 7. 성능 벤치마크

### 7.1. 목표 성능 지표

| 메트릭 | 목표값 | 측정 방법 |
|--------|--------|-----------|
| **검색 시간 (L2)** | < 50ms | 평균 응답 시간 |
| **검색 시간 (L3)** | < 200ms | 평균 응답 시간 |
| **검색 정확도** | > 0.8 | 유사도 임계값 기준 |
| **캐시 히트율** | > 60% | 캐시 사용률 |
| **인덱스 크기** | < 1GB | 데이터 10만 건 기준 |

### 7.2. 모니터링

```python
import time
from dataclasses import dataclass

@dataclass
class SearchMetrics:
    search_time: float
    results_count: int
    cache_hit: bool
    search_level: str

class SearchMonitor:
    def __init__(self):
        self.metrics: List[SearchMetrics] = []
    
    def record_search(self, metrics: SearchMetrics):
        """검색 메트릭 기록"""
        self.metrics.append(metrics)
    
    def get_stats(self) -> Dict:
        """통계 정보 조회"""
        if not self.metrics:
            return {}
        
        avg_time = sum(m.search_time for m in self.metrics) / len(self.metrics)
        cache_hit_rate = sum(1 for m in self.metrics if m.cache_hit) / len(self.metrics)
        
        return {
            "avg_search_time": avg_time,
            "cache_hit_rate": cache_hit_rate,
            "total_searches": len(self.metrics)
        }
```

---

## 8. 참고 자료

- **pgvector 공식 문서**: https://github.com/pgvector/pgvector
- **HNSW 알고리즘**: https://arxiv.org/abs/1603.09320
- **메모리 계층 아키텍처**: `docs/planning/06_hardware_memory_strategy.md`
- **데이터베이스 스키마**: `docs/backend/db.md`
