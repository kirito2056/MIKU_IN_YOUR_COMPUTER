"""MediaPipe Tasks 모델(.task) 다운로드 → backend/models/mediapipe/

사용법: (backend/) python scripts/download_vision_models.py
"""

import sys
from pathlib import Path

import requests

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")  # Windows cp949 콘솔에서 이모지 출력

BACKEND_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BACKEND_DIR / "models" / "mediapipe"

BASE = "https://storage.googleapis.com/mediapipe-models"
MODELS = {
    "face_landmarker.task": f"{BASE}/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
    "gesture_recognizer.task": f"{BASE}/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task",
    "pose_landmarker_lite.task": f"{BASE}/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
}


def main() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    for name, url in MODELS.items():
        dest = MODEL_DIR / name
        if dest.exists() and dest.stat().st_size > 0:
            print(f"✅ {name} (이미 있음, {dest.stat().st_size // 1024} KB)")
            continue
        print(f"⬇️  {name} 다운로드 중...")
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        dest.write_bytes(r.content)
        print(f"✅ {name} ({len(r.content) // 1024} KB)")
    print(f"\n모델 위치: {MODEL_DIR}")


if __name__ == "__main__":
    main()
