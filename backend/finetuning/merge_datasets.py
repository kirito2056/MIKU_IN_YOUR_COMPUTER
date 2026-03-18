"""
커스텀 대화 데이터를 기존 데이터셋에 병합하는 스크립트.
사용법:
  python finetuning/merge_datasets.py
  python finetuning/merge_datasets.py --custom custom_my.json
  python finetuning/merge_datasets.py --custom a.json b.json --out datasets/miku_merged_chat.json
"""
import json
import argparse
from pathlib import Path


def load_chat_json(path: Path) -> list:
    """Chat 형식 JSON 로드. messages 키가 있는 항목만 유효."""
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


def main():
    base_dir = Path(__file__).parent
    datasets_dir = base_dir / "datasets"
    default_base = datasets_dir / "miku_personality_chat.json"
    default_out = datasets_dir / "miku_personality_chat.json"

    parser = argparse.ArgumentParser(description="미쿠 파인튜닝 데이터셋 병합")
    parser.add_argument(
        "--base",
        type=Path,
        default=default_base,
        help="기준 데이터셋 경로 (기본: datasets/miku_personality_chat.json)",
    )
    parser.add_argument(
        "--custom",
        type=Path,
        nargs="*",
        default=[],
        help="추가할 JSON 파일 경로 (여러 개 가능)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=default_out,
        help="병합 결과 저장 경로 (기본: 덮어쓰기)",
    )
    args = parser.parse_args()

    # 기준 데이터 로드
    if not args.base.exists():
        print(f"[오류] 기준 파일 없음: {args.base}")
        print("  먼저 python finetuning/create_dataset.py 를 실행하세요.")
        return 1

    merged = load_chat_json(args.base)
    print(f"[기준] {args.base.name}: {len(merged)}개")

    # 커스텀 파일들 병합
    for p in args.custom:
        if not p.exists():
            print(f"[경고] 파일 없음, 건너뜀: {p}")
            continue
        added = load_chat_json(p)
        merged.extend(added)
        print(f"[추가] {p.name}: {len(added)}개")

    # 저장
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    print(f"[OK] 병합 완료: {args.out} (총 {len(merged)}개)")
    return 0


if __name__ == "__main__":
    exit(main())
