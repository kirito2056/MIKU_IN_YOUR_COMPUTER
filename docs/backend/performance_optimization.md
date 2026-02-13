# 성능 최적화 전략 (Performance Optimization Strategy)

## 1. 개요

MIKU 시스템의 전반적인 성능을 최적화하여 사용자 경험을 향상시키고, 하드웨어 리소스를 효율적으로 활용합니다.

**참고 문서**:
- 하드웨어 구성: `docs/planning/06_hardware_memory_strategy.md`
- 벡터 검색 최적화: `docs/backend/vector_search_optimization.md`
- 시스템 모니터링: `docs/backend/monitoring.md`

---

## 2. 캐싱 전략

### 2.1. LLM 응답 캐싱

동일한 질문에 대한 응답을 캐싱하여 반복적인 LLM 추론을 방지합니다.

#### A. 캐시 키 생성
```python
import hashlib
import json
from typing import Dict, Optional

def generate_cache_key(
    user_input: str,
    context: Dict,
    model_name: str = "gemma-3-27b-4bit"
) -> str:
    """LLM 응답 캐시 키 생성"""
    # 사용자 입력 + 컨텍스트 해시
    cache_data = {
        "input": user_input.strip().lower(),
        "context_summary": hash(str(context)),  # 컨텍스트 요약
        "model": model_name
    }
    cache_string = json.dumps(cache_data, sort_keys=True)
    return hashlib.sha256(cache_string.encode()).hexdigest()
```

#### B. 캐시 저장소
```python
from datetime import datetime, timedelta
from typing import Optional
import redis  # 또는 메모리 기반 캐시

class LLMResponseCache:
    def __init__(self, ttl_seconds: int = 3600):
        self.cache = {}  # 또는 Redis 클라이언트
        self.ttl = ttl_seconds
    
    def get(self, cache_key: str) -> Optional[str]:
        """캐시에서 응답 조회"""
        cached = self.cache.get(cache_key)
        if cached and cached['expires_at'] > datetime.now():
            return cached['response']
        return None
    
    def set(self, cache_key: str, response: str):
        """응답을 캐시에 저장"""
        self.cache[cache_key] = {
            'response': response,
            'expires_at': datetime.now() + timedelta(seconds=self.ttl),
            'created_at': datetime.now()
        }
    
    def invalidate(self, pattern: str = None):
        """캐시 무효화 (선택적 패턴 매칭)"""
        if pattern:
            # 패턴 매칭으로 부분 무효화
            keys_to_delete = [k for k in self.cache.keys() if pattern in k]
            for key in keys_to_delete:
                del self.cache[key]
        else:
            # 전체 캐시 클리어
            self.cache.clear()
```

#### C. 캐시 통합
```python
class CachedLLMService:
    def __init__(self, llm_service, cache: LLMResponseCache):
        self.llm_service = llm_service
        self.cache = cache
    
    async def generate_response(
        self,
        user_input: str,
        context: Dict
    ) -> str:
        """캐싱이 적용된 LLM 응답 생성"""
        # 캐시 키 생성
        cache_key = generate_cache_key(user_input, context)
        
        # 캐시 확인
        cached_response = self.cache.get(cache_key)
        if cached_response:
            return cached_response
        
        # 캐시 미스: LLM 추론 수행
        response = await self.llm_service.generate(user_input, context)
        
        # 캐시 저장
        self.cache.set(cache_key, response)
        
        return response
```

**캐시 전략**:
- **TTL**: 1시간 (동일한 질문에 대한 응답은 1시간 동안 재사용)
- **저장 위치**: RAM (빠른 접근)
- **캐시 크기**: 최대 1000개 응답
- **무효화**: 성격 매트릭스 업데이트 시 관련 캐시 무효화

### 2.2. 벡터 검색 결과 캐싱

벡터 검색 결과를 캐싱하여 반복적인 DB 쿼리를 방지합니다.

**참고**: 상세 내용은 `docs/backend/vector_search_optimization.md` 참조

```python
class VectorSearchCache:
    def __init__(self, max_size: int = 100):
        self.cache = {}
        self.max_size = max_size
    
    def _get_cache_key(self, query_embedding: np.ndarray) -> str:
        """임베딩 벡터를 해시하여 캐시 키 생성"""
        return hashlib.md5(query_embedding.tobytes()).hexdigest()
    
    def get(self, query_embedding: np.ndarray) -> Optional[List[Dict]]:
        """캐시에서 검색 결과 조회"""
        key = self._get_cache_key(query_embedding)
        return self.cache.get(key)
    
    def set(self, query_embedding: np.ndarray, results: List[Dict]):
        """검색 결과를 캐시에 저장"""
        key = self._get_cache_key(query_embedding)
        if len(self.cache) >= self.max_size:
            # LRU: 가장 오래된 항목 제거
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        self.cache[key] = {
            'results': results,
            'timestamp': datetime.now()
        }
```

### 2.3. TTS 오디오 캐싱

동일한 텍스트에 대한 TTS 오디오를 캐싱하여 반복적인 음성 합성을 방지합니다.

```python
import os
from pathlib import Path

class TTSAudioCache:
    def __init__(self, cache_dir: Path = Path("C:/MIKU_DATA/cache/tts/")):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_path(self, text: str, voice_model: str = "miku") -> Path:
        """텍스트와 음성 모델을 기반으로 캐시 파일 경로 생성"""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        return self.cache_dir / f"{voice_model}_{text_hash}.wav"
    
    def get(self, text: str, voice_model: str = "miku") -> Optional[Path]:
        """캐시된 오디오 파일 경로 반환 (존재 시)"""
        cache_path = self._get_cache_path(text, voice_model)
        if cache_path.exists():
            return cache_path
        return None
    
    def set(self, text: str, audio_data: bytes, voice_model: str = "miku"):
        """오디오 데이터를 캐시 파일로 저장"""
        cache_path = self._get_cache_path(text, voice_model)
        cache_path.write_bytes(audio_data)
    
    def cleanup_old_files(self, max_age_days: int = 7):
        """오래된 캐시 파일 정리"""
        cutoff_time = datetime.now().timestamp() - (max_age_days * 24 * 3600)
        for cache_file in self.cache_dir.glob("*.wav"):
            if cache_file.stat().st_mtime < cutoff_time:
                cache_file.unlink()
```

**캐시 전략**:
- **저장 위치**: SSD (C:/MIKU_DATA/cache/tts/)
- **파일 형식**: WAV (무손실)
- **정리 주기**: 주 1회 (7일 이상 된 파일 삭제)
- **예상 용량**: 텍스트당 약 50KB (1분 오디오 기준)

### 2.4. Vision 처리 결과 캐싱

동일한 프레임에 대한 Vision 처리 결과를 캐싱합니다.

```python
class VisionCache:
    def __init__(self, max_size: int = 50):
        self.cache = {}
        self.max_size = max_size
    
    def _get_cache_key(self, frame_hash: str, source: str) -> str:
        """프레임 해시와 소스를 기반으로 캐시 키 생성"""
        return f"{source}_{frame_hash}"
    
    def get(self, frame_hash: str, source: str) -> Optional[Dict]:
        """캐시에서 Vision 처리 결과 조회"""
        key = self._get_cache_key(frame_hash, source)
        cached = self.cache.get(key)
        if cached and cached['timestamp'] > datetime.now() - timedelta(seconds=5):
            # 5초 이내 프레임만 캐시 유효
            return cached['result']
        return None
    
    def set(self, frame_hash: str, source: str, result: Dict):
        """Vision 처리 결과를 캐시에 저장"""
        key = self._get_cache_key(frame_hash, source)
        if len(self.cache) >= self.max_size:
            # 가장 오래된 항목 제거
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]['timestamp'])
            del self.cache[oldest_key]
        self.cache[key] = {
            'result': result,
            'timestamp': datetime.now()
        }
```

**캐시 전략**:
- **TTL**: 5초 (동일 프레임은 5초 동안 재사용)
- **저장 위치**: RAM
- **캐시 크기**: 최대 50개 프레임

---

## 3. 배치 처리 전략

### 3.1. 메모리 계층 이동 배치 처리

L1 → L2, L2 → L3 이동을 배치로 처리하여 I/O 오버헤드를 최소화합니다.

```python
from typing import List, Dict
import asyncio

class MemoryTierManager:
    def __init__(self, db_pool, batch_size: int = 100):
        self.db_pool = db_pool
        self.batch_size = batch_size
        self.l1_to_l2_buffer: List[Dict] = []
        self.l2_to_l3_buffer: List[Dict] = []
    
    async def move_l1_to_l2(self, conversations: List[Dict]):
        """L1 (RAM) → L2 (SSD) 배치 이동"""
        self.l1_to_l2_buffer.extend(conversations)
        
        # 버퍼가 임계값을 초과하면 배치로 DB에 저장
        if len(self.l1_to_l2_buffer) >= self.batch_size:
            await self._flush_l1_to_l2()
    
    async def _flush_l1_to_l2(self):
        """L1 → L2 버퍼를 DB에 배치 저장"""
        if not self.l1_to_l2_buffer:
            return
        
        # 임베딩 생성 (배치)
        embeddings = await self._generate_embeddings_batch(
            [conv['content'] for conv in self.l1_to_l2_buffer]
        )
        
        # 배치 INSERT
        async with self.db_pool.acquire() as conn:
            await conn.executemany("""
                INSERT INTO conversations (id, timestamp, speaker, content, embedding, emotion)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, [
                (
                    conv['id'],
                    conv['timestamp'],
                    conv['speaker'],
                    conv['content'],
                    embedding.tolist(),
                    conv.get('emotion')
                )
                for conv, embedding in zip(self.l1_to_l2_buffer, embeddings)
            ])
        
        # 버퍼 클리어
        self.l1_to_l2_buffer.clear()
    
    async def move_l2_to_l3(self, archive_date: datetime):
        """L2 (SSD) → L3 (HDD) 배치 아카이브 (수면 모드 시 실행)"""
        # 오래된 데이터 조회
        async with self.db_pool.acquire() as conn:
            old_conversations = await conn.fetch("""
                SELECT * FROM conversations
                WHERE timestamp < $1
                ORDER BY timestamp
                LIMIT $2
            """, archive_date, self.batch_size)
        
        if not old_conversations:
            return
        
        # HDD 아카이브에 저장 (SQLite 또는 JSONL)
        await self._archive_to_l3([dict(row) for row in old_conversations])
        
        # L2에서 삭제 (선택적: 보관 정책에 따라)
        # await conn.execute("DELETE FROM conversations WHERE id = ANY($1)", [ids])
    
    async def _archive_to_l3(self, conversations: List[Dict]):
        """L3 아카이브 저장 (HDD)"""
        archive_path = Path("D:/MIKU_DATA/vault/") / f"archive_{datetime.now().strftime('%Y%m')}.jsonl"
        with archive_path.open('a') as f:
            for conv in conversations:
                f.write(json.dumps(conv) + '\n')
```

**배치 처리 전략**:
- **L1 → L2**: 대화가 100턴 이상 쌓일 때 배치로 이동
- **L2 → L3**: 수면 모드 시 배치로 아카이브
- **배치 크기**: 100개 (성능 테스트를 통해 조정)

### 3.2. 로그 처리 배치

로그 파일 쓰기를 버퍼링하여 I/O 오버헤드를 최소화합니다.

```python
import logging
from logging.handlers import BufferingHandler
from pathlib import Path

class BatchedFileHandler(BufferingHandler):
    def __init__(self, log_dir: Path, capacity: int = 100, flush_interval: int = 60):
        super().__init__(capacity)
        self.log_dir = log_dir
        self.flush_interval = flush_interval
        self.last_flush = datetime.now()
    
    def shouldFlush(self, record):
        """버퍼가 가득 찼거나 시간 간격이 지나면 플러시"""
        if len(self.buffer) >= self.capacity:
            return True
        if (datetime.now() - self.last_flush).seconds >= self.flush_interval:
            return True
        return False
    
    def flush(self):
        """버퍼의 로그를 파일에 배치 쓰기"""
        if not self.buffer:
            return
        
        # 로그 레벨별 파일 분리
        log_files = {
            'INFO': self.log_dir / 'info' / f"{datetime.now().strftime('%Y-%m-%d_%H')}.log",
            'WARNING': self.log_dir / 'warning' / f"{datetime.now().strftime('%Y-%m-%d_%H')}.log",
            'ERROR': self.log_dir / 'error' / f"{datetime.now().strftime('%Y-%m-%d_%H')}.log",
            'CRITICAL': self.log_dir / 'critical' / f"{datetime.now().strftime('%Y-%m-%d_%H')}.log"
        }
        
        # 레벨별로 그룹화
        logs_by_level = {}
        for record in self.buffer:
            level = logging.getLevelName(record.levelno)
            if level not in logs_by_level:
                logs_by_level[level] = []
            logs_by_level[level].append(self.format(record))
        
        # 배치 쓰기
        for level, logs in logs_by_level.items():
            if level in log_files:
                log_file = log_files[level]
                log_file.parent.mkdir(parents=True, exist_ok=True)
                with log_file.open('a') as f:
                    f.write('\n'.join(logs) + '\n')
        
        # 버퍼 클리어
        self.buffer.clear()
        self.last_flush = datetime.now()
```

**배치 처리 전략**:
- **버퍼 크기**: 100개 로그
- **플러시 간격**: 60초
- **파일 분리**: 로그 레벨별로 별도 파일

### 3.3. DB 쿼리 배치

여러 대화 로그를 한 번에 INSERT하여 쿼리 오버헤드를 최소화합니다.

```python
async def batch_insert_conversations(
    db_pool: asyncpg.Pool,
    conversations: List[Dict],
    embeddings: List[np.ndarray]
):
    """대화 로그를 배치로 INSERT"""
    async with db_pool.acquire() as conn:
        # executemany를 사용한 배치 INSERT
        await conn.executemany("""
            INSERT INTO conversations (id, timestamp, speaker, content, embedding, emotion)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (id) DO NOTHING
        """, [
            (
                conv['id'],
                conv['timestamp'],
                conv['speaker'],
                conv['content'],
                emb.tolist(),
                conv.get('emotion')
            )
            for conv, emb in zip(conversations, embeddings)
        ])
```

---

## 4. GPU 리소스 관리

### 4.1. VRAM 최적화

#### A. 모델 로딩 전략

```python
from typing import Optional
import torch

class ModelManager:
    def __init__(self):
        self.loaded_models = {}
        self.model_paths = {
            'llm': 'D:/MIKU_DATA/models/gemma-3-27b-4bit.gguf',  # GPU 0 (RTX 5080)
            'tts': 'D:/MIKU_DATA/models/gpt-sovits-miku.pt',  # GPU 1 (RTX 3090)
            'vision': 'D:/MIKU_DATA/models/yolo-v8.pt'  # GPU 1 (RTX 3090)
        }
    
    def load_model(self, model_name: str, device: str = 'cuda:0') -> torch.nn.Module:
        """모델을 VRAM에 로딩 (Lazy Loading)"""
        if model_name in self.loaded_models:
            return self.loaded_models[model_name]
        
        # GPU 할당 결정
        if model_name == 'llm':
            device = 'cuda:0'  # RTX 5080 (Main LLM 전용)
        elif model_name in ['tts', 'vision']:
            device = 'cuda:1'  # RTX 3090 (서브 작업)
        
        # VRAM 사용량 확인
        if device.startswith('cuda'):
            vram_used = torch.cuda.memory_allocated(device) / 1024**3  # GB
            vram_total = torch.cuda.get_device_properties(device).total_memory / 1024**3
            if vram_used / vram_total > 0.9:  # 90% 이상 사용 중
                # 다른 모델 언로딩 필요 (LLM은 제외)
                self._unload_unused_models()
        
        # 모델 로딩
        model = self._load_model_from_disk(model_name, device)
        self.loaded_models[model_name] = model
        return model
    
    def _unload_unused_models(self):
        """사용하지 않는 모델 언로딩"""
        # 우선순위: LLM > TTS > Vision
        # LLM은 GPU 0 (RTX 5080)에서 전용으로 사용되므로 언로딩하지 않음
        # Vision과 TTS는 GPU 1 (RTX 3090)에서 사용되며 필요시 언로딩 가능
        priority_order = ['vision', 'tts']  # LLM은 언로딩하지 않음
        
        for model_name in priority_order:
            if model_name in self.loaded_models:
                del self.loaded_models[model_name]
                torch.cuda.empty_cache()
                break
    
    def unload_model(self, model_name: str):
        """모델 언로딩 및 VRAM 해제"""
        if model_name in self.loaded_models:
            del self.loaded_models[model_name]
            torch.cuda.empty_cache()
```

#### B. Stateless 실행 (컨텍스트 관리)

```python
class StatelessLLMService:
    def __init__(self, model_manager: ModelManager):
        self.model_manager = model_manager
        self.llm_model = None
    
    async def generate(self, prompt: str, context: Dict) -> str:
        """Stateless 방식으로 LLM 추론 수행"""
        # 1. 모델 로딩 (필요 시)
        if self.llm_model is None:
            self.llm_model = self.model_manager.load_model('llm', device='cuda:0')
        
        # 2. 컨텍스트를 VRAM으로 복사
        context_tensor = self._prepare_context(context)
        
        # 3. 추론 수행
        response = await self._inference(prompt, context_tensor)
        
        # 4. 컨텍스트 해제 (VRAM에서 제거)
        del context_tensor
        torch.cuda.empty_cache()
        
        return response
```

### 4.2. GPU 할당 전략

#### A. 작업 우선순위 기반 할당

```python
from enum import IntEnum

class TaskPriority(IntEnum):
    LLM_INFERENCE = 1  # 최우선
    TTS = 2
    STT = 3
    VISION = 4
    SD_GENERATION = 5  # 최저 우선순위

class GPUScheduler:
    def __init__(self):
        self.gpu_0 = 'cuda:0'  # RTX 5080 (Main LLM)
        self.gpu_1 = 'cuda:1'  # RTX 3090 (Vision AI, TTS, STT, SD)
        self.gpu_usage = {
            self.gpu_0: {'tasks': [], 'vram_used': 0},
            self.gpu_1: {'tasks': [], 'vram_used': 0}
        }
    
    def allocate_gpu(self, task_type: TaskPriority) -> str:
        """작업 유형에 따라 GPU 할당"""
        if task_type == TaskPriority.LLM_INFERENCE:
            return self.gpu_0  # 항상 GPU 0 (RTX 5080) 사용 - Main LLM 전용
        
        # Vision, TTS, STT, SD 등 모든 서브 작업은 GPU 1 (RTX 3090) 사용
        return self.gpu_1
    
    def check_gpu_availability(self, gpu: str) -> bool:
        """GPU 사용 가능 여부 확인"""
        vram_used = torch.cuda.memory_allocated(gpu) / 1024**3
        vram_total = torch.cuda.get_device_properties(gpu).total_memory / 1024**3
        return vram_used / vram_total < 0.9  # 90% 미만이면 사용 가능
```

### 4.3. 모델 프리로딩

자주 사용하는 모델을 미리 로딩하여 첫 사용 시 지연을 방지합니다.

```python
class ModelPreloader:
    def __init__(self, model_manager: ModelManager):
        self.model_manager = model_manager
        self.preload_queue = []
    
    async def preload_common_models(self):
        """자주 사용하는 모델을 미리 로딩"""
        # LLM은 항상 로딩 (최우선)
        self.model_manager.load_model('llm', device='cuda:0')
        
        # TTS는 유휴 시간에 로딩
        if self._is_idle():
            self.model_manager.load_model('tts', device='cuda:1')
    
    def _is_idle(self) -> bool:
        """시스템이 유휴 상태인지 확인"""
        # 최근 5분간 LLM 추론이 없으면 유휴로 판단
        ...
```

---

## 5. 데이터베이스 쿼리 최적화

### 5.1. 인덱스 전략

#### A. 자주 검색되는 컬럼에 인덱스 생성

```sql
-- 시간 기반 검색 최적화
CREATE INDEX idx_conversations_timestamp ON conversations(timestamp DESC);

-- 화자별 검색 최적화
CREATE INDEX idx_conversations_speaker ON conversations(speaker);

-- 복합 인덱스 (시간 + 화자)
CREATE INDEX idx_conversations_timestamp_speaker 
ON conversations(timestamp DESC, speaker);

-- 벡터 검색 인덱스 (pgvector)
CREATE INDEX idx_conversations_embedding 
ON conversations USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

#### B. 인덱스 모니터링

```sql
-- 인덱스 사용 통계 확인
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,  -- 인덱스 스캔 횟수
    idx_tup_read,  -- 읽은 튜플 수
    idx_tup_fetch  -- 가져온 튜플 수
FROM pg_stat_user_indexes
WHERE tablename = 'conversations'
ORDER BY idx_scan DESC;

-- 사용되지 않는 인덱스 확인
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND schemaname = 'public';
```

### 5.2. 쿼리 최적화 기법

#### A. N+1 쿼리 문제 해결

```python
# 나쁜 예: N+1 쿼리
async def get_conversations_with_emotions_bad(conversation_ids: List[str]):
    conversations = []
    for conv_id in conversation_ids:
        conv = await db.fetchrow("SELECT * FROM conversations WHERE id = $1", conv_id)
        emotion = await db.fetchrow("SELECT * FROM emotions WHERE conversation_id = $1", conv_id)
        conversations.append({**conv, 'emotion': emotion})
    return conversations

# 좋은 예: JOIN 사용
async def get_conversations_with_emotions_good(conversation_ids: List[str]):
    return await db.fetch("""
        SELECT 
            c.*,
            e.emotion_data
        FROM conversations c
        LEFT JOIN emotions e ON c.id = e.conversation_id
        WHERE c.id = ANY($1)
    """, conversation_ids)
```

#### B. 페이지네이션

```python
async def get_conversations_paginated(
    page: int = 1,
    page_size: int = 50
) -> Dict:
    """페이지네이션을 사용한 대화 로그 조회"""
    offset = (page - 1) * page_size
    
    async with db_pool.acquire() as conn:
        # 전체 개수 조회
        total_count = await conn.fetchval("SELECT COUNT(*) FROM conversations")
        
        # 페이지 데이터 조회
        conversations = await conn.fetch("""
            SELECT * FROM conversations
            ORDER BY timestamp DESC
            LIMIT $1 OFFSET $2
        """, page_size, offset)
        
        return {
            'data': [dict(row) for row in conversations],
            'total': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size
        }
```

### 5.3. 연결 풀링

```python
import asyncpg

# 연결 풀 생성
db_pool = await asyncpg.create_pool(
    host='localhost',
    port=5432,
    database='miku_db',
    user='miku_user',
    password='miku_password',
    min_size=5,  # 최소 연결 수
    max_size=20,  # 최대 연결 수
    max_queries=50000,  # 연결당 최대 쿼리 수
    max_inactive_connection_lifetime=300  # 비활성 연결 유지 시간 (초)
)
```

---

## 6. 프론트엔드 성능 최적화

### 6.1. 렌더링 최적화

#### A. 3D 모델 LOD (Level of Detail)

```typescript
import { useFrame } from '@react-three/fiber'
import { useRef } from 'react'

function MikuModel({ distance }: { distance: number }) {
  const modelRef = useRef<THREE.Group>()
  
  // 거리에 따라 LOD 적용
  const lodLevel = distance > 10 ? 'low' : distance > 5 ? 'medium' : 'high'
  
  useFrame(() => {
    if (modelRef.current) {
      // 거리에 따라 모델 품질 조정
      modelRef.current.traverse((child) => {
        if (child instanceof THREE.Mesh) {
          child.geometry.computeBoundingSphere()
          // LOD에 따라 메시 품질 조정
        }
      })
    }
  })
  
  return <primitive ref={modelRef} object={model} />
}
```

#### B. 프레임레이트 동적 조절

```typescript
import { useFrame } from '@react-three/fiber'

function AdaptiveFrameRate() {
  const [targetFPS, setTargetFPS] = useState(60)
  
  useFrame((state, delta) => {
    // 상호작용 중: 60fps
    // 대기 중: 30fps
    const isInteracting = state.pointer.isActive
    setTargetFPS(isInteracting ? 60 : 30)
    
    // 프레임 제한
    if (delta < 1 / targetFPS) {
      return
    }
  })
}
```

#### C. 불필요한 리렌더링 방지

```typescript
import { memo, useMemo } from 'react'

// React.memo로 불필요한 리렌더링 방지
const MikuCharacter = memo(({ emotion, position }: Props) => {
  // useMemo로 계산 결과 캐싱
  const animationConfig = useMemo(() => {
    return getAnimationConfig(emotion)
  }, [emotion])
  
  return <MikuModel config={animationConfig} position={position} />
})
```

### 6.2. 네트워크 최적화

#### A. WebSocket 메시지 압축

```typescript
import pako from 'pako'

class CompressedWebSocket {
  private ws: WebSocket
  
  send(data: any) {
    const json = JSON.stringify(data)
    const compressed = pako.deflate(json)
    this.ws.send(compressed)
  }
  
  onMessage(callback: (data: any) => void) {
    this.ws.onmessage = (event) => {
      const decompressed = pako.inflate(event.data, { to: 'string' })
      const data = JSON.parse(decompressed)
      callback(data)
    }
  }
}
```

#### B. 오디오 스트리밍 최적화

```typescript
// 청크 크기 조절로 지연 최소화
const AUDIO_CHUNK_SIZE = 4096  // 4KB 청크

async function streamAudio(audioData: ArrayBuffer) {
  const chunks = []
  for (let i = 0; i < audioData.byteLength; i += AUDIO_CHUNK_SIZE) {
    chunks.push(audioData.slice(i, i + AUDIO_CHUNK_SIZE))
  }
  
  // 청크 단위로 스트리밍
  for (const chunk of chunks) {
    await playAudioChunk(chunk)
  }
}
```

---

## 7. 시스템 리소스 모니터링 및 자동 조정

### 7.1. 동적 임계값 조정

시스템 부하에 따라 성능 파라미터를 자동으로 조정합니다.

```python
class AdaptivePerformanceManager:
    def __init__(self):
        self.current_load = 0.0
        self.performance_mode = 'normal'  # 'normal', 'high', 'low'
    
    def update_load(self, cpu_usage: float, gpu_usage: float, memory_usage: float):
        """시스템 부하 업데이트"""
        self.current_load = (cpu_usage + gpu_usage + memory_usage) / 3
        
        # 부하에 따라 성능 모드 조정
        if self.current_load > 0.8:
            self.performance_mode = 'low'
        elif self.current_load > 0.6:
            self.performance_mode = 'normal'
        else:
            self.performance_mode = 'high'
    
    def get_optimization_params(self) -> Dict:
        """현재 성능 모드에 따른 최적화 파라미터 반환"""
        if self.performance_mode == 'low':
            return {
                'llm_context_window': 2048,  # 컨텍스트 축소
                'tts_quality': 'fast',  # 빠른 TTS
                'vision_fps': 1,  # Vision 처리 빈도 감소
                'render_fps': 30  # 렌더링 프레임레이트 감소
            }
        elif self.performance_mode == 'normal':
            return {
                'llm_context_window': 4096,
                'tts_quality': 'balanced',
                'vision_fps': 3,
                'render_fps': 60
            }
        else:  # high
            return {
                'llm_context_window': 8192,
                'tts_quality': 'high',
                'vision_fps': 5,
                'render_fps': 60
            }
```

### 7.2. 성능 병목 지점 자동 감지

```python
import time
from dataclasses import dataclass
from typing import List

@dataclass
class PerformanceMetric:
    operation: str
    duration: float
    timestamp: datetime

class PerformanceProfiler:
    def __init__(self):
        self.metrics: List[PerformanceMetric] = []
        self.thresholds = {
            'llm_inference': 2.0,  # 2초
            'tts_generation': 1.0,  # 1초
            'vector_search': 0.1,  # 100ms
            'vision_processing': 0.5  # 500ms
        }
    
    def record_operation(self, operation: str, duration: float):
        """작업 수행 시간 기록"""
        metric = PerformanceMetric(operation, duration, datetime.now())
        self.metrics.append(metric)
        
        # 임계값 초과 시 경고
        if operation in self.thresholds and duration > self.thresholds[operation]:
            self._handle_bottleneck(operation, duration)
    
    def _handle_bottleneck(self, operation: str, duration: float):
        """성능 병목 지점 처리"""
        # 로그 기록
        logger.warning(f"Performance bottleneck detected: {operation} took {duration:.2f}s")
        
        # 자동 조정 (예: 캐시 활성화, 배치 크기 조정)
        if operation == 'llm_inference':
            # LLM 응답 캐싱 강화
            ...
        elif operation == 'vector_search':
            # 벡터 검색 캐시 활성화
            ...
    
    def get_bottlenecks(self, time_window: int = 300) -> List[Dict]:
        """최근 N초간의 병목 지점 분석"""
        cutoff = datetime.now() - timedelta(seconds=time_window)
        recent_metrics = [m for m in self.metrics if m.timestamp > cutoff]
        
        bottlenecks = {}
        for metric in recent_metrics:
            if metric.operation in self.thresholds:
                if metric.duration > self.thresholds[metric.operation]:
                    if metric.operation not in bottlenecks:
                        bottlenecks[metric.operation] = []
                    bottlenecks[metric.operation].append(metric.duration)
        
        return [
            {
                'operation': op,
                'avg_duration': sum(durations) / len(durations),
                'max_duration': max(durations),
                'count': len(durations)
            }
            for op, durations in bottlenecks.items()
        ]
```

---

## 8. 성능 벤치마크 및 목표

### 8.1. 목표 성능 지표

| 메트릭 | 목표값 | 측정 방법 |
|--------|--------|-----------|
| **LLM 응답 시간** | < 2초 | 평균 응답 시간 |
| **TTS 생성 시간** | < 1초 | 평균 생성 시간 |
| **벡터 검색 시간 (L2)** | < 50ms | 평균 검색 시간 |
| **벡터 검색 시간 (L3)** | < 200ms | 평균 검색 시간 |
| **Vision 처리 시간** | < 500ms | 평균 처리 시간 |
| **캐시 히트율 (LLM)** | > 30% | 캐시 사용률 |
| **캐시 히트율 (TTS)** | > 50% | 캐시 사용률 |
| **캐시 히트율 (Vector)** | > 60% | 캐시 사용률 |
| **프레임레이트 (대기)** | 30fps | 평균 FPS |
| **프레임레이트 (상호작용)** | 60fps | 평균 FPS |

### 8.2. 모니터링 대시보드

```python
class PerformanceDashboard:
    def __init__(self):
        self.profiler = PerformanceProfiler()
        self.cache_stats = {}
        self.gpu_stats = {}
    
    def get_summary(self) -> Dict:
        """성능 요약 정보"""
        return {
            'cache_hit_rates': self.cache_stats,
            'gpu_usage': self.gpu_stats,
            'bottlenecks': self.profiler.get_bottlenecks(),
            'avg_response_time': self._calculate_avg_response_time()
        }
    
    def _calculate_avg_response_time(self) -> float:
        """평균 응답 시간 계산"""
        llm_metrics = [m for m in self.profiler.metrics if m.operation == 'llm_inference']
        if not llm_metrics:
            return 0.0
        return sum(m.duration for m in llm_metrics) / len(llm_metrics)
```

---

## 9. 참고 자료

- **벡터 검색 최적화**: `docs/backend/vector_search_optimization.md`
- **시스템 모니터링**: `docs/backend/monitoring.md`
- **하드웨어 전략**: `docs/planning/06_hardware_memory_strategy.md`
- **에러 로깅**: `docs/backend/error_logging.md`
