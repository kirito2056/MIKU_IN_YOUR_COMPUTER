# Gemma 4 메타데이터 수정 가이드

Gemma 4(및 Hugging Face 모델)와 관련된 메타데이터는 아래와 같이 수정할 수 있습니다.

---

## 0. "넌 사용자를 도와주는 채팅 AI야" 같은 문구 (시스템 프롬프트 느낌)

그런 **역할을 정해 주는 문장**은 보통 두 군데에서 올 수 있습니다.

1. **모델 학습 시**  
   Instruct 계열 모델(Gemma-IT 등)은 학습할 때 “You are a helpful assistant” 같은 지시가 포함된 데이터로 훈련돼 있어서, **별도 문구 없이도** 도우미처럼 답하는 경향이 있습니다. 즉 “도와주는 AI” 느낌은 **모델 안에 이미 들어 있는 것**에 가깝습니다.

2. **채팅 템플릿 / 첫 메시지**  
   일부 모델·서비스는 `tokenizer_config.json`의 **채팅 템플릿**에 고정 문구를 넣거나, 매 대화마다 **첫 번째 user 메시지**로 “넌 ~ AI야”를 붙여서 시스템 프롬프트처럼 씁니다.

**Gemma 4는 시스템 역할(system role)을 공식 지원하지 않습니다.**  
그래서 “이런 역할이야”라는 문구를 쓰고 싶다면:

- **방법 A (추천)**  
  우리 앱에서 **매 대화 시작 시 첫 user 메시지**로 넣기.  
  예: `[{"role": "user", "content": "넌 미쿠야. 마스터를 도와주는 존재로만 답해.\n\n" + 사용자_메시지}]`
- **방법 B**  
  LoRA/모델과 함께 쓰는 **토크나이저**의 `tokenizer_config.json` 안 `chat_template`을 수정해서, 대화가 시작될 때 항상 같은 지시 문구가 **앞에 붙도록** Jinja2로 넣기. (이 경우 “시스템 프롬프트처럼” 동작하는 고정 문구를 템플릿에서 관리하는 셈입니다.)

정리하면, **“넌 ~ AI야” 같은 텍스트는 시스템 프롬프트처럼 쓰이는 문구가 맞고**, Gemma 4에서는 (1) 모델 학습에 이미 반영된 “도우미” 성향 + (2) 우리가 넣는 **첫 user 메시지** 또는 **채팅 템플릿 고정 문구**로 수정·추가할 수 있습니다.

## 1. 수정 가능한 메타데이터 종류

### 1.1. 모델 디렉토리 내 파일 (로컬 모델만)

모델을 로컬에 다운로드한 경우(`backend/models/Gemma4_12B/` 또는 `D:/MIKU_DATA/models/` 등), 해당 폴더 안의 JSON 파일을 직접 편집할 수 있습니다.

| 파일 | 용도 | 수정 시 주의 |
|------|------|--------------|

| `config.json` | 모델 구조, hidden size, layer 수 등 | 값을 잘못 바꾸면 로딩 실패. 주로 `model_type`, `torch_dtype` 등 참고용으로만 변경 권장. |
| `tokenizer_config.json` | **채팅 템플릿**(`chat_template`), 특수 토큰, 채팅 포맷 | 대화 포맷을 바꾸고 싶을 때 수정. Jinja2 문법 사용. |
| `generation_config.json` | 기본 생성 옵션 (max_new_tokens, temperature 등) | 추론 시 기본값 변경 시 수정. |

**채팅 템플릿 예시** (`tokenizer_config.json`의 `chat_template`):

- Gemma 4는 시스템 역할을 공식 지원하지 않습니다. “넌 ~ AI야” 같은 **역할 지시**는 **첫 번째 user 메시지**에 넣거나, 템플릿 맨 앞에 고정 문구를 두는 방식으로 넣습니다.
- 템플릿 문법은 [Hugging Face 채팅 템플릿 문서](https://huggingface.co/docs/transformers/main/en/chat_template_advanced) 참고.

### 1.2. 프로젝트 LoRA 메타데이터 (`metadata.json`)

파인튜닝 시 출력 디렉토리(`outputs/miku_lora/`)에 **자동으로** 저장됩니다.

- **위치**: `backend/finetuning/outputs/miku_lora/metadata.json`
- **내용**: 베이스 모델, 데이터셋 경로, 에포크, 학습률, LoRA 설정, 학습 일시 등
- **수정**: 학습 후 JSON 파일을 직접 열어서 버전 번호, 메모, 데이터셋 설명 등을 추가해도 됩니다.

예시:

```json
{
  "base_model": "models/Gemma4_12B",
  "dataset_path": "datasets/miku_chat",
  "num_epochs": 3,
  "batch_size": 4,
  "learning_rate": 0.0002,
  "lora_r": 16,
  "lora_alpha": 32,
  "use_4bit": true,
  "trained_at": "2025-02-15T12:00:00Z"
}
```

여기에 `"version": "1.0"`, `"note": "첫 미쿠 성격 반영"` 같은 필드를 추가해 두면 나중에 버전 관리에 유용합니다.

## 2. 토크나이저만 수정해서 저장하기 (채팅 포맷 변경)

모델 가중치는 그대로 두고, **채팅 포맷만** 바꾸고 싶다면 토크나이저를 로드한 뒤 수정하고 저장하면 됩니다.

```python
from pathlib import Path
from transformers import AutoTokenizer

model_path = "models/Gemma4_12B"  # 또는 google/gemma-4-12B-it
tokenizer = AutoTokenizer.from_pretrained(model_path)

# 채팅 템플릿 변경 (필요 시)
# tokenizer.chat_template = "..."  # Jinja2 문자열

# 수정된 토크나이저 저장 (로컬 모델일 때만 덮어쓰기 주의)
out_dir = Path("finetuning/outputs/miku_lora")
out_dir.mkdir(parents=True, exist_ok=True)
tokenizer.save_pretrained(out_dir)
```

LoRA와 함께 쓸 때는 보통 **LoRA 저장 경로**에 토크나이저를 저장하므로, 해당 경로의 `tokenizer_config.json`을 편집해도 적용됩니다.

## 3. 요약

| 목적 | 수정 대상 |
|------|-----------|
| 대화 포맷/채팅 템플릿 변경 | 모델 또는 LoRA 출력 폴더의 `tokenizer_config.json` |
| 추론 기본값 변경 | `generation_config.json` 또는 코드에서 `generate(..., max_new_tokens=...)` |
| 학습 이력/버전 관리 | `outputs/miku_lora/metadata.json` (학습 시 자동 생성, 필요 시 필드 추가) |
| 모델 구조 관련 값 참고/변경 | `config.json` (변경 시 로딩 오류 가능성 있음, 신중히) |

**정리**: Gemma 4 메타데이터는 **수정 가능**합니다. 채팅 포맷은 `tokenizer_config.json`, 학습/버전 정보는 `metadata.json`을 활용하면 됩니다.
