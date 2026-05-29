"""
커스텀 대화 데이터를 데이터셋에 병합합니다.

1) 한 파일에 합쳐 저장 (보내기·단일 파일 학습용)
   python finetuning/merge_datasets.py \\
     --base datasets/miku_chat --custom datasets/custom_miku_example.json \\
     --out datasets/miku_merged_chat.json

2) 특정 샤드 JSON에 이어 붙이기 (폴더 구조 유지)
   python finetuning/merge_datasets.py \\
     --into datasets/miku_chat/playful_daily/chat.json \\
     --custom datasets/custom_miku_example.json
"""
import json
import argparse
from pathlib import Path


def load_chat_json(path: Path) -> list:
    """단일 JSON: messages 항목만."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"{path}: 루트는 배열이어야 합니다.")
    out = []
    for i, item in enumerate(data):
        if isinstance(item, dict) and "messages" in item:
            out.append(item)
        else:
            print(f"  [경고] {path} 항목 {i} 건너뜀 (messages 없음)")
    return out


def load_base(base: Path) -> list:
    if base.is_file():
        return load_chat_json(base)
    if base.is_dir():
        merged = []
        for fp in sorted(base.rglob("*.json")):
            if fp.name.startswith("_"):
                continue
            merged.extend(load_chat_json(fp))
        return merged
    raise FileNotFoundError(f"기준 경로 없음: {base}")


def main():
    base_dir = Path(__file__).parent
    datasets_dir = base_dir / "datasets"
    default_base = datasets_dir / "miku_chat"

    parser = argparse.ArgumentParser(description="미쿠 파인튜닝 Chat 데이터 병합")
    parser.add_argument(
        "--base",
        type=Path,
        default=None,
        help="기준: 디렉터리(miku_chat) 또는 단일 JSON",
    )
    parser.add_argument(
        "--into",
        type=Path,
        default=None,
        help="이 JSON 배열 파일 끝에 custom 항목을 이어 붙임 (--base/--out과 동시 사용 안 함)",
    )
    parser.add_argument(
        "--custom",
        type=Path,
        nargs="*",
        default=[],
        help="추가할 JSON 파일 경로",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="병합 결과 단일 JSON (--into 미사용 시 권장)",
    )
    args = parser.parse_args()

    if args.into is not None:
        if args.base is not None or args.out is not None:
            print("[오류] --into 는 --base / --out 과 함께 쓰지 마세요.")
            return 1
        if not args.into.exists():
            print(f"[오류] --into 파일 없음: {args.into}")
            return 1
        merged = load_chat_json(args.into)
        for p in args.custom:
            if not p.exists():
                print(f"[경고] 파일 없음: {p}")
                continue
            added = load_chat_json(p)
            merged.extend(added)
            print(f"[추가] {p.name}: +{len(added)}개")
        with open(args.into, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        print(f"[OK] 갱신: {args.into} (총 {len(merged)}개)")
        return 0

    base = args.base if args.base is not None else default_base
    if not base.exists():
        print(f"[오류] 기준 없음: {base}")
        return 1

    merged = load_base(base)
    print(f"[기준] {base}: {len(merged)}개")

    for p in args.custom:
        if not p.exists():
            print(f"[경고] 파일 없음, 건너뜀: {p}")
            continue
        added = load_chat_json(p)
        merged.extend(added)
        print(f"[추가] {p.name}: {len(added)}개")

    out = args.out
    if out is None:
        out = datasets_dir / "miku_merged_chat.json"
        print(f"[안내] --out 생략 → {out}")

    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    print(f"[OK] 병합 완료: {out} (총 {len(merged)}개)")
    print("  단일 파일로 학습: python finetuning/train_lora.py --dataset_path datasets/miku_merged_chat.json")
    return 0


if __name__ == "__main__":
    exit(main())
