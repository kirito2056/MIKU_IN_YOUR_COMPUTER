# 파인튜닝 모듈

미쿠의 성격에 맞게 Gemma 4 12B 모델을 파인튜닝하는 도구들입니다.

## 빠른 시작

### 1. 초기 데이터셋 생성

```bash
python finetuning/create_dataset.py
```

성격 매트릭스 기반 초기 대화 데이터셋을 생성합니다.

## Gemma 4 12B QLoRA (권장)

### 1. 모델 다운로드

```bash
cd backend
python scripts/download_gemma4_12b.py
```

약관 동의: https://huggingface.co/google/gemma-4-12B-it

### 2. QLoRA 학습

```bash
cd backend/finetuning
python train_lora_gemma4.py \
    --model_name models/Gemma4_12B \
    --dataset_path datasets/miku_chat \
    --num_epochs 3 \
    --use_4bit
```

RTX 5080 16GB 기본값: `batch_size=1`, `grad_accum=8`, `max_seq_length=512`

### 3. 테스트

```bash
python test_model.py --gemma4 --base_model models/Gemma4_12B --lora_path models/outputs/miku_gemma4_v1 --mode test
```

## Gemma 3 LoRA (레거시)

```bash
# 로컬 모델 사용 (backend/models/Gemma4_12B 폴더)
python finetuning/train_lora.py \
    --model_name models/Gemma4_12B \
    --dataset_path datasets/miku_chat \
    --output_dir outputs/miku_lora \
    --num_epochs 3 \
    --use_4bit

# 또는 HuggingFace 모델 사용
python finetuning/train_lora.py \
    --model_name google/gemma-4-12B-it \
    --dataset_path datasets/miku_chat \
    --output_dir outputs/miku_lora \
    --num_epochs 3 \
    --use_4bit
```

### 3. 모델 테스트

```bash
# 성격 테스트 (로컬 모델 사용, 기본값: models/Gemma4_12B)
python finetuning/test_model.py --mode test

# 대화형 채팅
python finetuning/test_model.py --mode chat

# 다른 모델 경로 지정
python finetuning/test_model.py \
    --base_model models/Gemma4_12B \
    --lora_path outputs/miku_lora \
    --mode chat
```

## 파일 구조

- `create_dataset.py`: 성격 매트릭스 시드 → `miku_matrix_seed_chat.json` 덤프
- `split_miku_dataset.py`: 단일 Chat JSON → `datasets/miku_chat/<상황>/chat.json` 분할·응답 변형
- `merge_datasets.py`: 커스텀 JSON 병합 (`--into` 로 샤드에 이어 붙이기 또는 `--out` 단일 파일)
- `train_lora_gemma4.py`: Gemma 4 12B QLoRA 파인튜닝
- `train_lora.py`: Gemma 3 LoRA 파인튜닝 (레거시)
- `test_model.py`: 파인튜닝된 모델 테스트 스크립트
- `datasets/miku_chat/`: 상황·감정별 Chat JSON (기본 학습 경로, 구조는 `docs/ai/miku_chat_dataset.md`)
- `datasets/custom_miku_example.json`: 커스텀 데이터 템플릿
- `outputs/`: 학습된 LoRA 어댑터 저장 디렉토리

### 파인튜닝용 데이터 추가하기

1. **형식**: `datasets/custom_miku_example.json` 처럼 `messages` 배열 (user/assistant).
2. **병합**: `python finetuning/merge_datasets.py --into datasets/miku_chat/playful_daily/chat.json --custom datasets/내대화.json`  
   또는 전체를 한 파일로: `--base datasets/miku_chat --custom ... --out datasets/miku_merged_chat.json`
3. **학습**: 기본은 `--dataset_path datasets/miku_chat` (디렉터리 전체 로드). 단일 파일이면 해당 `.json` 경로 지정.

## 상세 가이드

- 파인튜닝 절차: `docs/ai/finetuning_guide.md`
- **Gemma 4 메타데이터 수정** (채팅 템플릿, config, metadata.json): `docs/ai/gemma_metadata.md`
