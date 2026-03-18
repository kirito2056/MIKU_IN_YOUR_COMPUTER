# 파인튜닝 모듈

미쿠의 성격에 맞게 Gemma 3 모델을 파인튜닝하는 도구들입니다.

## 빠른 시작

### 1. 초기 데이터셋 생성

```bash
python finetuning/create_dataset.py
```

성격 매트릭스 기반 초기 대화 데이터셋을 생성합니다.

### 2. LoRA 파인튜닝 실행

```bash
# 로컬 모델 사용 (backend/models/Gemma_12B 폴더)
python finetuning/train_lora.py \
    --model_name models/Gemma_12B \
    --dataset_path datasets/miku_personality_chat.json \
    --output_dir outputs/miku_lora \
    --num_epochs 3 \
    --use_4bit

# 또는 HuggingFace 모델 사용
python finetuning/train_lora.py \
    --model_name google/gemma-3-27b-it \
    --dataset_path datasets/miku_personality_chat.json \
    --output_dir outputs/miku_lora \
    --num_epochs 3 \
    --use_4bit
```

### 3. 모델 테스트

```bash
# 성격 테스트 (로컬 모델 사용, 기본값: models/Gemma_12B)
python finetuning/test_model.py --mode test

# 대화형 채팅
python finetuning/test_model.py --mode chat

# 다른 모델 경로 지정
python finetuning/test_model.py \
    --base_model models/Gemma_27B \
    --lora_path outputs/miku_lora \
    --mode chat
```

## 파일 구조

- `create_dataset.py`: 초기 데이터셋 생성 스크립트
- `merge_datasets.py`: 커스텀 JSON을 기존 데이터셋에 병합
- `train_lora.py`: LoRA 파인튜닝 스크립트
- `test_model.py`: 파인튜닝된 모델 테스트 스크립트
- `datasets/`: 데이터셋 저장 디렉토리
  - `miku_personality_chat.json`: 학습용 Chat 형식 (기본 사용)
  - `miku_personality_alpaca.json`: Alpaca 형식
  - `custom_miku_example.json`: 커스텀 데이터 추가 시 참고용 템플릿
- `outputs/`: 학습된 LoRA 어댑터 저장 디렉토리

### 파인튜닝용 데이터 추가하기

1. **새 대화 추가**: `datasets/custom_miku_example.json` 형식을 참고해 `messages` 배열로 user/assistant 대화를 JSON 파일에 작성합니다.
2. **병합**: `python finetuning/merge_datasets.py --custom datasets/내대화.json` 으로 기존 데이터셋에 병합합니다.
3. **학습**: `--dataset_path datasets/miku_personality_chat.json` 으로 파인튜닝을 실행합니다.

## 상세 가이드

- 파인튜닝 절차: `docs/ai/finetuning_guide.md`
- **Gemma 메타데이터 수정** (채팅 템플릿, config, metadata.json): `docs/ai/gemma_metadata.md`
