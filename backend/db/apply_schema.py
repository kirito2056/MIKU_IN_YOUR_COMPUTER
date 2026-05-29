#!/usr/bin/env python3
"""
PostgreSQL + pgvector 스키마 적용

사용법 (backend 디렉터리에서):
  python db/apply_schema.py
  python db/apply_schema.py --dry-run

환경 변수:
  DATABASE_URL=postgresql://miku:miku@localhost:5432/miku
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

try:
    import psycopg2
except ImportError:
    print("psycopg2가 필요합니다: pip install psycopg2-binary")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

DB_DIR = Path(__file__).resolve().parent
SCHEMA_DIR = DB_DIR / "schema"


def get_dsn() -> str:
    if load_dotenv:
        load_dotenv(DB_DIR.parent / ".env")
        load_dotenv()
    return os.getenv(
        "DATABASE_URL",
        "postgresql://miku:miku@localhost:5432/miku",
    )


def list_sql_files() -> list[Path]:
    return sorted(SCHEMA_DIR.glob("*.sql"))


def applied_versions(conn) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'schema_migrations'
            """
        )
        if cur.fetchone() is None:
            return set()
        cur.execute("SELECT version FROM schema_migrations")
        return {row[0] for row in cur.fetchall()}


def apply_file(conn, path: Path, dry_run: bool) -> None:
    sql = path.read_text(encoding="utf-8")
    version = path.name
    if dry_run:
        print(f"  [dry-run] {version} ({len(sql)} bytes)")
        return
    with conn.cursor() as cur:
        cur.execute(sql)
        cur.execute(
            """
            INSERT INTO schema_migrations (version)
            VALUES (%s)
            ON CONFLICT (version) DO NOTHING
            """,
            (version,),
        )
    conn.commit()
    print(f"  ✅ {version}")


def main() -> int:
    parser = argparse.ArgumentParser(description="MIKU DB schema apply")
    parser.add_argument("--dry-run", action="store_true", help="적용할 파일만 출력")
    parser.add_argument("--force", action="store_true", help="이미 적용된 파일도 재실행")
    args = parser.parse_args()

    files = list_sql_files()
    if not files:
        print(f"스키마 파일 없음: {SCHEMA_DIR}")
        return 1

    dsn = get_dsn()
    print(f"📦 DB: {dsn.split('@')[-1] if '@' in dsn else dsn}")
    print(f"   SQL 파일 {len(files)}개")

    if args.dry_run:
        for f in files:
            apply_file(None, f, dry_run=True)
        return 0

    conn = psycopg2.connect(dsn)
    try:
        done = applied_versions(conn) if not args.force else set()
        for path in files:
            if path.name in done and not args.force:
                print(f"  ⏭️  {path.name} (already applied)")
                continue
            try:
                apply_file(conn, path, dry_run=False)
            except Exception as exc:
                conn.rollback()
                print(f"  ❌ {path.name}: {exc}")
                return 1
    finally:
        conn.close()

    print("✅ 스키마 적용 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
