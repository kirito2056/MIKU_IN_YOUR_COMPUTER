# 파인튜닝 가이드 (Fine-tuning Guide)

## 개요

MIKU IN YOUR COMPUTER 프로젝트에서 Gemma 3 모델을 미쿠의 성격에 맞게 파인튜닝하는 방법을 안내합니다.

## 1. 준비 사항

### 1.1. 하드웨어 요구사항
- **GPU**: RTX 5080 (16GB VRAM) 권장
  - 4-bit 양자화 사용 시 최소 8GB VRAM 필요
  - CPU 모드도 가능하지만 매우 느림
- **RAM**: 최소 16GB 권장
- **저장공간**: 모델 다운로드 및 학습 데이터 저장용 여유 공간 필요

### 1.2. 소프트웨어 요구사항
- Python 3.11 이상
- CUDA 11.8 이상 (GPU 사용 시)
- 필요한 라이브러리: `requirements.txt` 참고

## 2. 초기 데이터셋 생성

성격 매트릭스 기반 초기 대화 데이터셋을 생성합니다.

```bash
cd backend
python finetuning/create_dataset.py
```

이 스크립트는 다음 파일들을 생성합니다:
- `finetuning/datasets/miku_personality_alpaca.json`: Alpaca 형식 데이터셋
- `finetuning/datasets/miku_personality_chat.json`: Chat 형식 데이터셋 (Gemma 3 Instruct용)

### 데이터셋 형식

#### Chat 형식 (권장)
```json
[
  {
    "messages": [
      {"role": "user", "content": "너는 누구야?"},
      {"role": "assistant", "content": "나는 미쿠야. 오빠가 나를 만들었잖아..."}
    ]
  }
]
```

#### Alpaca 형식
```json
[
  {
    "instruction": "너는 누구야?",
    "input": "",
    "output": "나는 미쿠야. 오빠가 나를 만들었잖아..."
  }
]
```

## 3. LoRA 파인튜닝 실행

### 3.1. 기본 실행

```bash
cd backend/finetuning
python train_lora.py \
    --model_name google/gemma-3-27b-it \
    --dataset_path datasets/miku_personality_chat.json \
    --output_dir outputs/miku_lora \
    --num_epochs 3 \
    --batch_size 4 \
    --learning_rate 2e-4 \
    --use_4bit
```

**기본 설정:**
- 모델: `google/gemma-3-27b-it` (27B 파라미터)
- 양자화: 4-bit (VRAM 약 16-17GB 사용, RTX 5080 16GB 권장)

**사용 가능한 Gemma 3 모델:**
- `google/gemma-3-1b-it`: 1B 파라미터 (테스트용, VRAM 4GB+)
- `google/gemma-3-4b-it`: 4B 파라미터 (VRAM 8GB+)
- `google/gemma-3-12b-it`: 12B 파라미터 (VRAM 16GB+)
- `google/gemma-3-27b-it`: 27B 파라미터 (기본, VRAM 16GB+ with 4-bit)

### 3.2. 주요 파라미터 설명

- `--model_name`: 파인튜닝할 모델 (Gemma 3 모델명)
- `--dataset_path`: 학습 데이터셋 경로
- `--output_dir`: LoRA 어댑터 저장 경로
- `--num_epochs`: 학습 에포크 수 (3-5 권장)
- `--batch_size`: 배치 크기 (GPU 메모리에 따라 조정)
- `--learning_rate`: 학습률 (2e-4 권장)
- `--lora_r`: LoRA rank (16 권장, 높을수록 더 많은 파라미터 학습)
- `--lora_alpha`: LoRA alpha (32 권장, 보통 r의 2배)
- `--use_4bit`: 4-bit 양자화 사용 (VRAM 절약)

### 3.3. GPU 메모리에 따른 설정

#### RTX 5080 (16GB)
```bash
python train_lora.py \
    --batch_size 4 \
    --lora_r 16 \
    --use_4bit
```

#### RTX 3090 (24GB)
```bash
python train_lora.py \
    --batch_size 8 \
    --lora_r 32 \
    --use_4bit
```

#### CPU 모드 (비권장, 매우 느림)
```bash
python train_lora.py \
    --batch_size 1 \
    --use_4bit false
```

## 4. 데이터셋 확장

### 4.1. 대화 로그 수집

실제 대화 로그를 수집하여 데이터셋을 확장합니다.

```python
# 예시: 대화 로그를 데이터셋 형식으로 변환
conversations = [
    {
        "user": "오늘 뭐 했어?",
        "assistant": "마스터와 8시간이나 같이 있었어. 게임도 하고, 코딩도 봤지."
    }
]

# Chat 형식으로 변환
dataset = []
for conv in conversations:
    dataset.append({
        "messages": [
            {"role": "user", "content": conv["user"]},
            {"role": "assistant", "content": conv["assistant"]}
        ]
    })
```

### 4.2. 데이터셋 병합

여러 데이터셋을 병합하여 사용할 수 있습니다.

```python
import json

# 여러 데이터셋 로드
datasets = []
for path in ["dataset1.json", "dataset2.json", "dataset3.json"]:
    with open(path, "r", encoding="utf-8") as f:
        datasets.extend(json.load(f))

# 병합하여 저장
with open("merged_dataset.json", "w", encoding="utf-8") as f:
    json.dump(datasets, f, ensure_ascii=False, indent=2)
```

## 5. 학습 모니터링

학습 중 다음 정보를 확인할 수 있습니다:
- 학습 가능한 파라미터 수
- 학습 손실 (Loss)
- 학습 진행 상황

학습 로그는 `outputs/miku_lora` 디렉토리에 저장됩니다.

## 6. 파인튜닝된 모델 사용

### 6.1. LoRA 어댑터 로드

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# 베이스 모델 로드 (4-bit 양자화)
from transformers import BitsAndBytesConfig

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
)

base_model = AutoModelForCausalLM.from_pretrained(
    "google/gemma-3-27b-it",
    quantization_config=bnb_config,
    device_map="auto"
)
tokenizer = AutoTokenizer.from_pretrained("google/gemma-3-27b-it")

# LoRA 어댑터 로드
model = PeftModel.from_pretrained(base_model, "outputs/miku_lora")

# 추론
messages = [{"role": "user", "content": "안녕"}]
input_text = tokenizer.apply_chat_template(messages, tokenize=False)
inputs = tokenizer(input_text, return_tensors="pt").to(model.device)
outputs = model.generate(**inputs, max_new_tokens=100)
response = tokenizer.decode(outputs[0], skip_special_tokens=True)
```

## 7. 학습 전략

### 7.1. 초기 파인튜닝
1. 성격 매트릭스 기반 초기 데이터셋으로 첫 파인튜닝
2. 3-5 에포크 학습
3. 기본 성격이 모델에 반영되었는지 확인

### 7.2. 점진적 학습
1. 대화 로그가 쌓일 때마다 데이터셋 확장
2. 기존 LoRA 어댑터에 추가 학습 (Continual Learning)
3. 주기적으로 전체 재학습 (월 1회 등)

### 7.3. 학습 스케줄링
- **Nightly Learning**: 밤에 자동으로 학습 (구현 예정)
- **Threshold-based**: 데이터가 일정량 쌓이면 학습 (구현 예정)

## 8. 문제 해결

### 8.1. Out of Memory (OOM)
- 배치 크기 줄이기 (`--batch_size 2` 또는 `1`)
- 4-bit 양자화 사용 (`--use_4bit`)
- LoRA rank 줄이기 (`--lora_r 8`)

### 8.2. 학습이 너무 느림
- GPU 사용 확인
- 배치 크기 늘리기 (메모리 허용 시)
- Gradient accumulation 사용 (이미 포함됨)

### 8.3. 모델이 원하는 대로 응답하지 않음
- 데이터셋 품질 확인
- 학습 에포크 수 늘리기
- 학습률 조정 (낮추기: `1e-4`, 높이기: `5e-4`)

## 9. 베스트 프랙티스

1. **데이터 품질**: 양보다 질이 중요합니다. 좋은 대화 샘플을 선별하세요.
2. **점진적 학습**: 한 번에 너무 많이 학습하지 말고, 점진적으로 확장하세요.
3. **백업**: 학습된 LoRA 어댑터는 정기적으로 백업하세요.
4. **테스트**: 학습 후 반드시 추론 테스트를 수행하여 성격이 잘 반영되었는지 확인하세요.
5. **버전 관리**: 각 학습 버전을 명확히 구분하여 관리하세요.

## 10. 다음 단계

- [ ] 대화 로그 수집 시스템 구현
- [ ] 자동 학습 스케줄링 구현
- [ ] Google Drive API 연동 (백업)
- [ ] 학습 모니터링 대시보드
- [ ] A/B 테스트 시스템 (여러 LoRA 버전 비교)
