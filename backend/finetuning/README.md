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
# 로컬 모델 사용 (backend/models 폴더)
python finetuning/train_lora.py \
    --model_name models \
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
# 성격 테스트 (로컬 모델 사용, 기본값: models)
python finetuning/test_model.py --mode test

# 대화형 채팅
python finetuning/test_model.py --mode chat

# 다른 모델 경로 지정
python finetuning/test_model.py \
    --base_model models \
    --lora_path outputs/miku_lora \
    --mode chat
```

## 파일 구조

- `create_dataset.py`: 초기 데이터셋 생성 스크립트
- `train_lora.py`: LoRA 파인튜닝 스크립트
- `test_model.py`: 파인튜닝된 모델 테스트 스크립트
- `datasets/`: 데이터셋 저장 디렉토리
- `outputs/`: 학습된 LoRA 어댑터 저장 디렉토리

## 상세 가이드

자세한 내용은 `docs/ai/finetuning_guide.md`를 참고하세요.
