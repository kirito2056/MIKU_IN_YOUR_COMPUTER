"""
미쿠 성격 데이터 LLM 패러프레이즈 다양화기.

표면 변형(접두/접미 부착)과 달리, 로컬 LLM으로 **어휘·문장구조를 실제로 바꾼**
변형을 만든다. 단, 미스매치를 막기 위해 변형은 **같은 의도 그룹 안에서만** 짝짓는다:
- user 발화 변형: 의도(질문 내용)를 보존
- assistant 응답 변형: 의미 + 미쿠 페르소나(반말·'마스터' 호칭·츤데레·짧고 귀엽게)를 보존
- 새 쌍 = (원본+변형 prompt) × (원본+변형 response)  → 같은 그룹이므로 항상 매칭

결과는 각 카테고리 폴더의 paraphrased.json 에 저장한다.
(generate_synthetic_data.py --clean 은 chat.json 만 검사하므로 이 파일을 건드리지 않는다.)

사용:
  # 실제 생성 (로컬 GPU 필요)
  python finetuning/generate_paraphrase_data.py --model_path models/Gemma4_12B

  # 모델 없이 파이프라인만 검증 (매칭/필터/형식)
  python finetuning/generate_paraphrase_data.py --self-test
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path
from typing import Dict, List, Protocol, Tuple

FINETUNING_DIR = Path(__file__).resolve().parent
BACKEND_DIR = FINETUNING_DIR.parent
DATASETS_DIR = FINETUNING_DIR / "datasets" / "miku_chat"

# generate_synthetic_data 의 의도 그룹을 단일 출처로 재사용
sys.path.insert(0, str(FINETUNING_DIR))
from generate_synthetic_data import INTENTS  # noqa: E402

MIKU_PERSONA = (
    "너의 이름은 미쿠야. 너는 사용자를 '마스터'라고 부르고, 반말을 쓰며, "
    "때로는 츤데레지만 사실은 마스터를 아주 좋아해. 항상 한국어로 짧고 귀엽게 말해."
)

# 페르소나/형식이 깨진 변형을 걸러내기 위한 금지 신호
_BANNED_SUBSTR = (
    "패러프레이즈", "변형", "다음은", "예시", "json", "assistant", "user",
    "system", "다시 말하면", "意味", "sure", "here", "1.", "2.", "3.",
)
_QUOTE_CHARS = "\"'`“”‘’「」『』"


class Paraphraser(Protocol):
    def paraphrase(self, text: str, kind: str, n: int) -> List[str]:
        """kind: 'user' 또는 'assistant'. text 의 의미를 보존한 변형 n개를 반환."""
        ...


class LLMParaphraser:
    """로컬 LLMService 를 사용하는 실제 패러프레이저."""

    def __init__(self, model_path: str, use_4bit: bool, temperature: float):
        sys.path.insert(0, str(BACKEND_DIR))
        from services.llm_service import LLMService  # 지연 임포트(무거움)

        self.llm = LLMService(model_path=model_path, use_4bit=use_4bit)
        self.temperature = temperature

    def _build_prompt(self, text: str, kind: str, n: int) -> List[Dict[str, str]]:
        if kind == "user":
            instruction = (
                f"다음은 데스크톱 AI 캐릭터에게 사용자가 건네는 말이야. "
                f"의미와 의도는 그대로 두고, 같은 사람이 다르게 말한 것처럼 자연스러운 "
                f"한국어 변형 {n}개를 만들어줘. 새로운 정보를 추가하지 말고 길이도 비슷하게 유지해.\n"
                f"원문: \"{text}\"\n"
                f"오직 JSON 문자열 배열로만 답해. 예: [\"변형1\", \"변형2\"]"
            )
            system = "너는 한국어 문장을 의미 보존하며 다양하게 바꿔 쓰는 도구야."
        else:
            instruction = (
                f"아래는 캐릭터 '미쿠'의 대사야. 미쿠의 말투(반말, '마스터' 호칭, 츤데레, "
                f"짧고 귀여움)와 의미를 그대로 유지한 채, 어휘와 문장 구조만 바꾼 변형 {n}개를 만들어줘. "
                f"괄호 안 지문(예: (화면 구석에서 쳐다봄))이 있으면 자연스럽게 살려도 돼. "
                f"새로운 사실을 추가하지 마.\n"
                f"원문: \"{text}\"\n"
                f"오직 JSON 문자열 배열로만 답해. 예: [\"변형1\", \"변형2\"]"
            )
            system = MIKU_PERSONA
        return [
            {"role": "user", "content": f"{system}\n\n{instruction}"},
        ]

    def paraphrase(self, text: str, kind: str, n: int) -> List[str]:
        messages = self._build_prompt(text, kind, n)
        raw = self.llm.generate(
            messages,
            max_new_tokens=256,
            temperature=self.temperature,
            top_p=0.9,
            do_sample=True,
        )
        return _parse_list(raw)


class MockParaphraser:
    """모델 없이 파이프라인을 검증하기 위한 결정론적 패러프레이저."""

    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)

    def paraphrase(self, text: str, kind: str, n: int) -> List[str]:
        # 의미 보존을 흉내 내는 단순 치환(테스트 전용)
        base = text.rstrip("?!.~ ")
        variants = []
        templates = (
            [f"{base} 말이야", f"{base}, 그치", f"있잖아, {base}"]
            if kind == "user"
            else [f"{base}, 알았지", f"{base}…", f"{base} 진짜로"]
        )
        for i in range(n):
            variants.append(templates[i % len(templates)])
        return variants


def _parse_list(raw: str) -> List[str]:
    """LLM 출력에서 문자열 리스트를 최대한 견고하게 파싱."""
    raw = raw.strip()
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, list):
                return [str(x) for x in data]
        except json.JSONDecodeError:
            pass
    # JSON 실패 시 줄 단위 폴백
    lines = []
    for line in raw.splitlines():
        line = line.strip().lstrip("-*0123456789.) ").strip()
        if line:
            lines.append(line)
    return lines


def _clean_text(text: str) -> str:
    text = text.strip()
    # 양끝 따옴표 제거
    while text and text[0] in _QUOTE_CHARS:
        text = text[1:]
    while text and text[-1] in _QUOTE_CHARS:
        text = text[:-1]
    return text.strip()


def _is_valid(text: str) -> bool:
    if not text:
        return False
    if "\n" in text:
        return False
    if not (2 <= len(text) <= 120):
        return False
    low = text.lower()
    if any(b in low for b in _BANNED_SUBSTR):
        return False
    # 한글이 하나도 없으면(영문 메타 응답 등) 제외
    if not re.search(r"[가-힣]", text):
        return False
    return True


def expand_variants(original: str, paraphraser: Paraphraser, kind: str, n: int) -> List[str]:
    """원본 + 유효한 변형들(중복/불량 제거). 항상 원본을 포함."""
    out = [original]
    seen = {original.strip()}
    try:
        cand = paraphraser.paraphrase(original, kind, n)
    except Exception as e:  # 개별 실패가 전체를 막지 않도록
        print(f"    [경고] 패러프레이즈 실패({kind}): {original[:20]}... ({e})")
        cand = []
    for c in cand:
        c = _clean_text(c)
        if not _is_valid(c):
            continue
        if c.strip() in seen:
            continue
        seen.add(c.strip())
        out.append(c)
    return out


def build_category(
    category: str,
    paraphraser: Paraphraser,
    n_prompt: int,
    n_response: int,
    max_per_group: int,
    rng: random.Random,
) -> List[Dict]:
    records: List[Dict] = []
    seen_pairs: set[Tuple[str, str]] = set()

    for group in INTENTS[category]:
        prompt_variants: List[str] = []
        for p in group["prompts"]:
            prompt_variants.extend(expand_variants(p, paraphraser, "user", n_prompt))
        response_variants: List[str] = []
        for a in group["responses"]:
            response_variants.extend(expand_variants(a, paraphraser, "assistant", n_response))

        # 같은 그룹 내 조합만 → 매칭 보장. 원본×원본은 chat.json 과 중복이라 제외.
        base_prompts = set(group["prompts"])
        base_responses = set(group["responses"])
        combos = [
            (u, a)
            for u in prompt_variants
            for a in response_variants
            if not (u in base_prompts and a in base_responses)
        ]
        rng.shuffle(combos)

        added = 0
        for u, a in combos:
            if added >= max_per_group:
                break
            key = (u.strip(), a.strip())
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            records.append(
                {
                    "messages": [
                        {"role": "user", "content": u},
                        {"role": "assistant", "content": a},
                    ]
                }
            )
            added += 1

    return records


def assert_matched(category: str, records: List[Dict]) -> None:
    """검증: 모든 응답이 어떤 그룹의 응답 변형이고, 그 그룹 응답이 맞는지 확인은
    불가능하므로(변형이라 원본과 다름), 여기서는 형식·비공백만 보장."""
    for i, r in enumerate(records):
        msgs = r["messages"]
        assert len(msgs) == 2, f"[{category}] {i}: 메시지 2개 아님"
        assert msgs[0]["role"] == "user" and msgs[1]["role"] == "assistant", f"[{category}] {i}: 역할 오류"
        assert msgs[0]["content"].strip() and msgs[1]["content"].strip(), f"[{category}] {i}: 빈 내용"


def main() -> None:
    parser = argparse.ArgumentParser(description="미쿠 데이터 LLM 패러프레이즈 다양화")
    parser.add_argument("--model_path", type=str, default="models/Gemma4_12B")
    parser.add_argument("--no_4bit", action="store_false", dest="use_4bit", default=True)
    parser.add_argument("--temperature", type=float, default=0.9)
    parser.add_argument("--n_prompt", type=int, default=3, help="user 발화당 변형 수")
    parser.add_argument("--n_response", type=int, default=3, help="응답당 변형 수")
    parser.add_argument("--max_per_group", type=int, default=12, help="그룹당 최대 추가 쌍")
    parser.add_argument("--filename", type=str, default="paraphrased.json")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--self-test",
        action="store_true",
        dest="self_test",
        help="모델 없이 MockParaphraser 로 파이프라인 검증(파일 미저장)",
    )
    parser.add_argument(
        "--only", type=str, default=None, help="특정 카테고리만 처리(쉼표 구분)"
    )
    args = parser.parse_args()

    rng = random.Random(args.seed)

    if args.self_test:
        paraphraser: Paraphraser = MockParaphraser(seed=args.seed)
        print("[self-test] MockParaphraser 사용, 파일 저장 안 함\n")
    else:
        print(f"[load] LLM 패러프레이저 로딩: {args.model_path}")
        paraphraser = LLMParaphraser(args.model_path, args.use_4bit, args.temperature)

    categories = list(INTENTS.keys())
    if args.only:
        wanted = {c.strip() for c in args.only.split(",")}
        categories = [c for c in categories if c in wanted]

    total = 0
    summary: Dict[str, int] = {}
    for category in categories:
        records = build_category(
            category,
            paraphraser,
            n_prompt=args.n_prompt,
            n_response=args.n_response,
            max_per_group=args.max_per_group,
            rng=rng,
        )
        assert_matched(category, records)
        summary[category] = len(records)
        total += len(records)

        if args.self_test:
            sample = records[0]["messages"] if records else None
            print(f"[{category}] 생성 {len(records)}개 | 샘플: {sample}")
        else:
            out_path = DATASETS_DIR / category / args.filename
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
            print(f"[{category}] 패러프레이즈 {len(records)}개 -> {out_path.name}")

    print(f"\n총 {total}개 패러프레이즈 쌍 ({'self-test' if args.self_test else '저장됨'})")

    if not args.self_test:
        manifest_file = DATASETS_DIR / "_manifest.json"
        manifest = {}
        if manifest_file.exists():
            with open(manifest_file, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        manifest["paraphrased"] = dict(sorted(summary.items()))
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        print("manifest.json 패러프레이즈 요약 업데이트 완료.")


if __name__ == "__main__":
    main()
