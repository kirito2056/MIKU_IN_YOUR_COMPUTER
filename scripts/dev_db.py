#!/usr/bin/env python3
"""
Docker postgres 기동 + 스키마 적용 (Windows/macOS/Linux)

  python scripts/dev_db.py
  python scripts/dev_db.py --reset
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"


def run(cmd: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=cwd or ROOT, check=check)


def wait_postgres_healthy(timeout_sec: int = 90) -> None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        proc = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Health.Status}}", "miku-postgres"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if proc.stdout.strip() == "healthy":
            return
        time.sleep(2)
    raise RuntimeError("postgres healthcheck timeout")


def main() -> int:
    parser = argparse.ArgumentParser(description="MIKU dev DB bootstrap (Docker)")
    parser.add_argument("--reset", action="store_true", help="docker compose down -v 후 재생성")
    args = parser.parse_args()

    if shutil.which("docker") is None:
        print("docker 명령을 찾을 수 없습니다. Docker Desktop을 설치·실행하세요.")
        return 1

    if args.reset:
        print("DB volume 삭제 후 재생성...")
        run(["docker", "compose", "down", "-v"])

    print("postgres 기동...")
    run(["docker", "compose", "up", "-d", "postgres"])

    print("healthcheck 대기...")
    wait_postgres_healthy()

    env_file = BACKEND / ".env"
    env_example = BACKEND / ".env.example"
    if not env_file.exists() and env_example.exists():
        env_file.write_text(env_example.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"생성됨: {env_file}")

    print("스키마 적용...")
    apply = run([sys.executable, "db/apply_schema.py"], cwd=BACKEND)
    if apply.returncode != 0:
        return apply.returncode

    print("완료. 확인: docker compose exec postgres psql -U miku -d miku -c '\\dt'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
