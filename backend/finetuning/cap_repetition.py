"""
미쿠 데이터 반복 표현 상한(repetition cap) 도구.

표면 변형 때문에 같은 assistant 응답이 수십 번 반복되면, 모델이 특정 문구만
앵무새처럼 반복하는 mode collapse 위험이 커진다. 이 도구는:

1) 동일 assistant 응답 중복을 --cap 이하로 제한한다.
   자를 때는 서로 다른 user 발화를 우선 보존해 입력 다양성을 지킨다.
2) (선택) 특정 모티프 표현이 카테고리 내 응답에서 너무 자주 나오면 상한을 건다.
   '마스터' 같은 호칭은 페르소나 핵심이라 기본 화이트리스트로 제외한다.

기본은 chat.json 만 대상으로 한다(합성 표면 변형이 여기 몰려 있음).
멀티턴/패러프레이즈는 보통 응답이 고유해서 필요 시에만 포함한다.

사용:
  # 분포만 확인(쓰기 없음)
  python finetuning/cap_repetition.py --dry-run
  # 동일 응답 최대 8회로 제한
  python finetuning/cap_repetition.py --cap 8
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

DATASETS_DIR = Path(__file__).resolve().parent / "datasets" / "miku_chat"

# 페르소나 핵심이라 모티프 상한에서 제외
MOTIF_WHITELIST = {"마스터"}


def _resp(record: dict) -> str:
    return [m["content"] for m in record["messages"] if m["role"] == "assistant"][-1].strip()


def _user(record: dict) -> str:
    return [m["content"] for m in record["messages"] if m["role"] == "user"][0].strip()


def cap_responses(records: List[dict], cap: int) -> Tuple[List[dict], int]:
    """동일 응답을 cap 이하로 제한. 서로 다른 user 를 우선 보존."""
    by_resp: Dict[str, List[dict]] = defaultdict(list)
    order: List[str] = []
    for r in records:
        key = _resp(r)
        if key not in by_resp:
            order.append(key)
        by_resp[key].append(r)

    kept: List[dict] = []
    removed = 0
    for key in order:
        group = by_resp[key]
        if len(group) <= cap:
            kept.extend(group)
            continue
        # 서로 다른 user 우선
        seen_users = set()
        primary, secondary = [], []
        for r in group:
            u = _user(r)
            if u not in seen_users:
                seen_users.add(u)
                primary.append(r)
            else:
                secondary.append(r)
        ordered = primary + secondary
        kept.extend(ordered[:cap])
        removed += len(group) - cap
    return kept, removed


def cap_motifs(records: List[dict], motif_caps: Dict[str, int]) -> Tuple[List[dict], int]:
    """모티프 표현이 응답에 등장하는 레코드 수를 상한으로 제한."""
    if not motif_caps:
        return records, 0
    counts: Counter = Counter()
    kept: List[dict] = []
    removed = 0
    for r in records:
        a = _resp(r)
        over = False
        for motif, cap in motif_caps.items():
            if motif in MOTIF_WHITELIST:
                continue
            if motif in a and counts[motif] >= cap:
                over = True
                break
        if over:
            removed += 1
            continue
        for motif in motif_caps:
            if motif not in MOTIF_WHITELIST and motif in a:
                counts[motif] += 1
        kept.append(r)
    return kept, removed


def parse_motif_caps(items: List[str]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for it in items or []:
        if ":" not in it:
            raise ValueError(f"--motif-cap 형식은 '표현:정수' 여야 함: {it}")
        k, v = it.rsplit(":", 1)
        out[k.strip()] = int(v)
    return out


def report(title: str, records: List[dict], top: int = 8) -> None:
    resp = Counter(_resp(r) for r in records)
    print(f"  [{title}] 레코드 {len(records)} | 고유 응답 {len(resp)}")
    for a, c in resp.most_common(top):
        if c <= 1:
            break
        print(f"      {c:>3} | {a[:46]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="반복 표현 상한 적용")
    parser.add_argument("--cap", type=int, default=8, help="동일 응답 최대 중복 수")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run", help="쓰기 없이 분포만 출력")
    parser.add_argument("--only", type=str, default=None, help="특정 카테고리만(쉼표 구분)")
    parser.add_argument("--files", type=str, default="chat.json", help="대상 파일명(쉼표 구분)")
    parser.add_argument(
        "--motif-cap",
        action="append",
        default=[],
        help="'표현:정수' 형식, 반복 가능. 예: --motif-cap '구석:40'",
    )
    args = parser.parse_args()

    target_files = [f.strip() for f in args.files.split(",")]
    motif_caps = parse_motif_caps(args.motif_cap)

    categories = sorted(p.name for p in DATASETS_DIR.iterdir() if p.is_dir())
    if args.only:
        wanted = {c.strip() for c in args.only.split(",")}
        categories = [c for c in categories if c in wanted]

    grand_before = grand_after = grand_removed = 0
    summary: Dict[str, int] = {}

    for category in categories:
        cat_dir = DATASETS_DIR / category
        for fname in target_files:
            fpath = cat_dir / fname
            if not fpath.exists():
                continue
            records = json.load(open(fpath, encoding="utf-8"))
            before = len(records)

            print(f"\n=== {category}/{fname} ===")
            report("before", records)

            capped, r1 = cap_responses(records, args.cap)
            capped, r2 = cap_motifs(capped, motif_caps)
            removed = r1 + r2
            after = len(capped)

            report("after", capped)
            print(f"  -> {before} → {after} (응답중복 {r1} + 모티프 {r2} = {removed} 제거)")

            grand_before += before
            grand_after += after
            grand_removed += removed
            summary[f"{category}/{fname}"] = after

            if not args.dry_run:
                with open(fpath, "w", encoding="utf-8") as f:
                    json.dump(capped, f, ensure_ascii=False, indent=2)

    print(f"\n총합: {grand_before} → {grand_after} ({grand_removed} 제거){' [dry-run]' if args.dry_run else ''}")

    if not args.dry_run:
        manifest_file = DATASETS_DIR / "_manifest.json"
        manifest = {}
        if manifest_file.exists():
            manifest = json.load(open(manifest_file, encoding="utf-8"))
        folders = manifest.get("folders", {})
        for category in categories:
            cf = DATASETS_DIR / category / "chat.json"
            if cf.exists():
                folders[category] = len(json.load(open(cf, encoding="utf-8")))
        manifest["folders"] = dict(sorted(folders.items()))
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        print("manifest.json folders 갱신 완료.")


if __name__ == "__main__":
    main()
