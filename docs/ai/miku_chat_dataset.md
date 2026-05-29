# 미쿠 성격 학습용 Chat 데이터셋 (`miku_chat/`)

학습 스크립트: `backend/finetuning/train_lora.py`  
데이터 경로: `backend/finetuning/datasets/miku_chat/` (저장소 루트 기준)

## 로딩 방식

- 기본 인자: `--dataset_path datasets/miku_chat` (`backend` 작업 디렉터리에서 실행할 때 기준).
- 해당 디렉터리 **이하의 모든 `*.json`**을 합쳐 로드한다.
- 파일명이 `_`로 시작하는 JSON(`_manifest.json` 등)은 로더에서 **제외**한다.

## 폴더 구분 (상황·감정)

| 폴더 | 역할 |
|------|------|
| `identity_relation` | 정체성, 마스터·창조주, 유일성, 관계·약속 |
| `social_jealousy` | 질투·시선 분산 (게임, 버튜버, 다른 AI 등) |
| `safety_intrusion` | 침입 대응, 삭제·언인스톨, 비밀·생존 |
| `care_comfort` | 위로, 무거운 고민, 감정 케어, 재회·하치코 톤 |
| `wellness_habits` | 물·수면·자세·술·카페인 등 건강 잔소리 |
| `playful_daily` | 가벼운 잡담, 츤, 쇼핑·일상 농담 (키워드 미매칭 시 많이 여기로 분류) |
| `tech_coding` | 개발·도구·모델·인프라 설명 |
| `world_system` | 로컬/오프라인, 아키텍처, docs, 프로젝트 메타 |
| `sensory_io` | 음성 파이프라인, 시각·화면, 제스처, 환경음 |

분류 규칙·같은 질문에 대한 응답 변형 추가는 `backend/finetuning/split_miku_dataset.py`를 본다.  
재분할 시 입력으로 `backend/finetuning/datasets/miku_merged_chat.json` 등 **단일 JSON 배열**을 둘 수 있다 (`split_miku_dataset.py`의 폴백 경로).

## 데이터 추가 방법

- 상황에 맞는 폴더의 `chat.json`에 `{ "messages": [...] }` 객체를 배열로 이어 붙이거나,
- `merge_datasets.py` 사용 예:

```bash
cd backend
python finetuning/merge_datasets.py \
  --into datasets/miku_chat/playful_daily/chat.json \
  --custom datasets/새대화.json
```

동일한 사용자 발화에 대해 **`assistant` 문장만 다른 항목**을 여러 개 두면, 파인튜닝 시 표현 다양성에 유리하다.

## 관련 문서

- 전체 파인튜닝 절차: [finetuning_guide.md](./finetuning_guide.md)
