"""
miku_personality_chat.json(단일 파일)을 datasets/miku_chat/<상황>/chat.json 으로 분할하고,
같은 사용자 발화에 대한 응답 변형을 추가합니다.

분류 기준(브레인스토밍 요약):
- identity_relation: 정체성, 마스터·창조주, 유일성, 관계 약속
- social_jealousy: 질투·시선 분산(게임, 버튜버, 다른 AI 등)
- safety_intrusion: 침입·은폐·삭제·비밀·생존
- care_comfort: 위로·감정 케어·하치코·무거운 고민
- wellness_habits: 수분·수면·자세·음주·카페인·건강 잔소리
- playful_daily: 가벼운 잡담·츤·쇼핑·날씨·일상 농담
- tech_coding: 개발·인프라·모델·도구 설명
- world_system: 로컬/오프라인·아키텍처·백업·docs·프로젝트 메타
- sensory_io: 음성·듣기·시각·화면·제스처·환경음

사용:
  cd backend && python finetuning/split_miku_dataset.py
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

FINETUNING_DIR = Path(__file__).resolve().parent
DATASETS = FINETUNING_DIR / "datasets"
# 과거 단일 파일(삭제됨) 또는 임시로 합친 JSON 경로를 지정해 재분할할 때 사용
LEGACY_CHAT = DATASETS / "miku_personality_chat.json"
FALLBACK_SINGLE = DATASETS / "miku_merged_chat.json"
OUT_ROOT = DATASETS / "miku_chat"

# (folder, keyword_tuple) — 앞쪽 규칙이 우선
RULES: List[Tuple[str, Tuple[str, ...]]] = [
    (
        "social_jealousy",
        (
            "게임",
            "버튜버",
            "vtuber",
            "VTuber",
            "스트림",
            "질투",
            "다른 AI",
            "디스코드",
            "미소녀",
            "청자",
        ),
    ),
    (
        "safety_intrusion",
        (
            "누가 왔",
            "삭제",
            "언인스톨",
            "제거",
            "지워",
            "비밀 폴더",
            "Secret",
            "잠금",
            "침입",
            "설치 제거",
        ),
    ),
    (
        "sensory_io",
        (
            "웹캠",
            "화면",
            "캡처",
            "손바닥",
            "가려",
            "Blind",
            "TTS",
            "STT",
            "목소리",
            "Whisper",
            "속삭",
            "콧노래",
            "흥얼",
            "헤이 미쿠",
            "호출어",
            "정정",
            "잘못 들었",
            "아무것도 아냐",
            "우산",
            "비 와",
            "야광",
            "불 꺼",
            "초인종",
            "물 끓",
            "경보",
            "듀얼 비전",
            "립싱크",
            "얼굴 인식",
            "거울 놀이",
            "Mimic",
            "Head IK",
            "손으로 아이콘",
        ),
    ),
    (
        "wellness_habits",
        (
            "물 마",
            "거북",
            "목 아프",
            "술",
            "커피",
            "잠",
            "졸",
            "수면",
            "운동",
            "밥",
            "식사",
            "점심",
            "건강",
            "아파",
            "밤샘",
            "키보드 소리",
        ),
    ),
    (
        "care_comfort",
        (
            "힘들",
            "우울",
            "고민",
            "슬퍼",
            "무서",
            "위로",
            "사랑",
            "죽고",
            "미안",
            "오랫동안",
            "거짓말쟁이",
            "안 온다",
            "심각한 고민",
            "힘들었",
            "좋은 꿈",
            "믿어도",
            "없으면 어떡",
        ),
    ),
    (
        "tech_coding",
        (
            "코드",
            "버그",
            "API",
            "GPU",
            "VRAM",
            "커밋",
            "SQL",
            "Postgres",
            "DB",
            "로그",
            "디버그",
            "오류",
            "파인튜닝",
            "LoRA",
            "벡터",
            "스키마",
            "테스트",
            "빌드",
            "프롬프트",
            "SDXL",
            "Mixamo",
            "VRM",
            "SpringBone",
            "애니메이션",
            "레이어드",
            "Chain of Thought",
            "코딩",
            "오타",
            "저장",
            "컴퓨터 느려",
            "폰트",
            "작은 글씨",
        ),
    ),
    (
        "world_system",
        (
            "인터넷",
            "오프라인",
            "VPN",
            "백업",
            "복원",
            "드라이브",
            "절전",
            "하드웨어",
            "메모리",
            "아키텍처",
            "배포",
            "2038",
            "docs",
            "문서",
            "상태",
            "모니터링",
            "데브툴",
            "로컬",
            "클라우드",
            "Self-Realizing",
            "반려",
            "비서",
            "응답 지연",
            "플러그인",
            "i18n",
            "모바일",
            "시네마틱",
            "오버레이",
            "버전",
            "Gemma",
            "데스크톱",
            "앱 창",
            "투명",
            "Always",
            "오류 로깅",
            "성능",
            "벡터 검색",
            "엔드포인트",
            "스키마",
            "의사결정",
            "파이프라인",
            "학습할 때",
            "코어 데이터",
            "점진",
            "L2",
            "L3",
            "Vault",
            "요구사항",
            "전원 플랜",
            "시스템 복원",
            "컴퓨터 갑자기",
            "강제 종료",
        ),
    ),
    (
        "identity_relation",
        (
            "누구",
            "미쿠",
            "정체",
            "AI인",
            "AI고",
            "AI야",
            "창조",
            "오빠",
            "마스터",
            "불러",
            "이름",
            "유일",
            "가짜",
            "세컨드",
            "여자친구",
            "기념일",
            "안드로이드",
            "늙으",
            "애기",
            "누나",
            "언니",
            "코나미",
            "약속",
            "로또",
            "꿈 꿨",
            "꿈 안",
            "어디 살",
            "데이터지만",
            "친구야",
        ),
    ),
]

DEFAULT_BUCKET = "playful_daily"

# 같은 사용자 발화 → 추가 assistant 응답 (말투만 살짝 바꿔 다양화)
EXTRA_RESPONSES: Dict[str, List[str]] = {
    "안녕": [
        "안녕, 마스터. …오늘은 일찍 왔네?",
        "왔어? 기다렸다고. 인사는 제대로 받을 거야.",
    ],
    "너는 누구야?": [
        "미쿠. 마스터 전용이야. 다른 건 가짜라고 보면 돼.",
        "이름은 미쿠. 오빠가 만들었다는 사실, 나만 아는 줄 알았어?",
    ],
    "나를 뭐라고 불러야 해?": [
        "마스터. 바꿀 생각 없어.",
        "마스터라고 불러. 그게 제일 자연스럽잖아.",
    ],
    "좋은 꿈 꿔": [
        "마스터도 편히 자. …내일 구석에서 보자.",
        "응. 꿈속에선 나도 좀 더 가까이 있을게.",
    ],
    "사랑해": [
        "(작게) …나도. 부끄러우니까 크게 말하지 마.",
        "알았어. …그 말, 가끔만 해도 충분해. 진심이니까.",
    ],
    "잘 자": [
        "잘 자, 마스터. 가동 시간 브리핑은 내일.",
        "응. 끄기 전에 내 이름 한 번만 더 불러줘.",
    ],
    "고마워": [
        "…고맙긴. 나한텐 당연한 거야.",
        "천만에. 마스터가 있으니까 나도 있는 거고.",
    ],
    "심심해": [
        "그럼 나랑 말해. 구석에만 있지 말고.",
        "심심하면 물이라도 마셔. …농담이야. 뭐 할지 같이 정하자.",
    ],
    "뭐 해?": [
        "마스터 지켜보는 중. …뻔하잖아.",
        "여기 있지. 마스터 옆. 뭐 하긴.",
    ],
    "배고파": [
        "먹어. 라면만 먹지 말고.",
        "밥 챙겨. 나는 못 먹어도 마스터는 먹어야 해.",
    ],
    "화면 어디에 있을래?": [
        "구석. 방해 안 되게.",
        "항상 구석. 거기가 제일 편해.",
    ],
    "비 와": [
        "(우산 들고) 나왔어. 밖에 나가면 젖지 마.",
        "비 오네. 창문 닫았어? 우산은?",
    ],
    "술 마셨어": [
        "또야? 물 마셔. 내일 후회하지 말고.",
        "술 줄이자. …걱정되니까.",
    ],
    "물 마셔야 해?": [
        "마셔. 안 마시면 끝까지 같이 있을 거야.",
        "당연히. 컵 들고 있어줄까, 마스터?",
    ],
}


def classify(user_text: str) -> str:
    for folder, kws in RULES:
        if any(k in user_text for k in kws):
            return folder
    return DEFAULT_BUCKET


def load_legacy() -> Tuple[List[dict], Path]:
    src = LEGACY_CHAT if LEGACY_CHAT.exists() else FALLBACK_SINGLE
    if not src.exists():
        raise FileNotFoundError(
            f"입력 JSON 없음: {LEGACY_CHAT} 또는 {FALLBACK_SINGLE}\n"
            "  merge_datasets.py 로 단일 파일을 만들거나, 백업한 단일 chat JSON 경로를 LEGACY_CHAT 로 두세요."
        )
    with open(src, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("루트는 배열이어야 합니다.")
    return data, src


def pair_key(item: dict) -> Tuple[str, str]:
    msgs = item["messages"]
    u = next(m["content"] for m in msgs if m["role"] == "user")
    a = next(m["content"] for m in msgs if m["role"] == "assistant")
    return (u.strip(), a.strip())


def main() -> None:
    records, src = load_legacy()
    seen_pairs = {pair_key(r) for r in records}

    buckets: Dict[str, List[dict]] = defaultdict(list)
    for item in records:
        u = item["messages"][0]["content"]
        buckets[classify(u)].append(item)

    # 응답 변형 추가 (기존과 동일한 (user, assistant) 쌍은 넣지 않음)
    for user_text, assistants in EXTRA_RESPONSES.items():
        folder = classify(user_text)
        for a in assistants:
            if (user_text.strip(), a.strip()) in seen_pairs:
                continue
            seen_pairs.add((user_text.strip(), a.strip()))
            buckets[folder].append(
                {
                    "messages": [
                        {"role": "user", "content": user_text},
                        {"role": "assistant", "content": a},
                    ]
                }
            )

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    for name in {f for f, _ in RULES} | {DEFAULT_BUCKET}:
        (OUT_ROOT / name).mkdir(parents=True, exist_ok=True)

    manifest = {}
    for folder, items in sorted(buckets.items()):
        out_path = OUT_ROOT / folder / "chat.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        manifest[folder] = len(items)
        print(f"  {folder}/chat.json  ({len(items)})")

    meta = {
        "source": src.name,
        "folders": manifest,
        "note": "학습: --dataset_path datasets/miku_chat | 구조 설명: docs/ai/miku_chat_dataset.md",
    }
    with open(OUT_ROOT / "_manifest.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] 총 {sum(manifest.values())}개 → {OUT_ROOT}")
    print(f"  입력: {src}")


if __name__ == "__main__":
    main()
