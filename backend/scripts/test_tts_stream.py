#!/usr/bin/env python3
"""
TTS 스트리밍 테스트 스크립트

사용법:
  1. GPT-SoVITS API 서버를 먼저 실행하세요 (아래 참고)
  2. python test_tts_stream.py "합성할 텍스트"
  3. python test_tts_stream.py  # 기본 문장으로 테스트

API 서버 실행 (GPT-SoVITS-v3 디렉터리에서):
  cd backend/models/GPT-SoVITS-v3
  python api.py -s SoVITS_weights_v3/MIKU_e3_s117_l32.pth -g GPT_weights_v3/MIKU-e15.ckpt ^
    -dr "voice/datasets/sliced/첫번째샘플.wav" -dt "참조텍스트" -dl ja -sm normal -mt ogg

  스트리밍: -sm normal
  비스트리밍(wav): -sm close (기본값)
"""
import argparse
import sys
from pathlib import Path

# 프로젝트 루트
ROOT = Path(__file__).resolve().parent.parent.parent
VOICE_ROOT = ROOT / "voice" / "datasets"
SLICED_LIST = VOICE_ROOT / "asr" / "sliced.list"
SLICED_DIR = VOICE_ROOT / "sliced"


def get_default_ref():
    """sliced.list에서 첫 번째 샘플을 참조 음원으로 사용"""
    if not SLICED_LIST.exists():
        return None, None
    with open(SLICED_LIST, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "|" not in line:
                continue
            parts = line.split("|", 3)
            path = parts[0].strip()
            text = parts[3].strip() if len(parts) > 3 else ""
            if Path(path).exists():
                return path, text
    return None, None


def test_tts(
    text: str,
    base_url: str = "http://127.0.0.1:9880",
    streaming: bool = True,
    ref_path: str = None,
    prompt_text: str = None,
    output_file: str = None,
):
    """
    TTS API 호출 (스트리밍 또는 전체)
    api.py 사용 시: GET /?text=...&refer_wav_path=...&prompt_text=...&prompt_language=ja&text_language=ja
    """
    import urllib.request
    import urllib.parse

    ref_path = ref_path or ""
    prompt_text = prompt_text or ""

    if not ref_path or not prompt_text:
        default_path, default_text = get_default_ref()
        ref_path = ref_path or default_path
        prompt_text = prompt_text or default_text

    if not ref_path:
        print("⚠️ 참조 음원을 찾을 수 없습니다. voice/datasets/asr/sliced.list 확인")
        return 1

    params = {
        "text": text,
        "text_language": "ja",
        "refer_wav_path": ref_path,
        "prompt_text": prompt_text,
        "prompt_language": "ja",
    }
    # stream_mode은 API 서버 시작 시 -sm normal 로 지정해야 함

    url = f"{base_url}/?{urllib.parse.urlencode(params)}"
    print(f"📡 요청: {base_url}/")
    print(f"   텍스트: {text[:50]}{'...' if len(text) > 50 else ''}")
    print(f"   참조: {Path(ref_path).name}")
    print(f"   스트리밍: {streaming}")
    print()

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=60) as resp:
            if resp.status != 200:
                body = resp.read().decode("utf-8", errors="replace")
                print(f"❌ 오류 {resp.status}: {body[:500]}")
                return 1

            chunks = []
            total = 0
            while True:
                chunk = resp.read(8192)
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
                if streaming:
                    print(f"\r   수신 중... {total:,} bytes", end="", flush=True)

            audio_data = b"".join(chunks)
            print(f"\n✅ 수신 완료: {len(audio_data):,} bytes")

            if output_file:
                out_path = Path(output_file)
            else:
                ext = "ogg" if streaming else "wav"
                default_out = ROOT / "output" / f"tts_test.{ext}"
                out_path = default_out
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "wb") as f:
                f.write(audio_data)
            print(f"   저장: {out_path}")
            if out_path.suffix.lower() in (".ogg", ".wav"):
                print("   재생: 윈도우에서 더블클릭 또는 media player로 열기")

            return 0

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else str(e)
        print(f"❌ HTTP 오류 {e.code}: {body[:500]}")
        return 1
    except Exception as e:
        print(f"❌ 오류: {e}")
        print("   API 서버가 실행 중인지 확인하세요. (python api.py ...)")
        return 1


def main():
    parser = argparse.ArgumentParser(description="TTS 스트리밍 테스트")
    parser.add_argument(
        "text",
        nargs="?",
        default="こんにちは、初音ミクです。よろしくね。",
        help="합성할 텍스트 (기본: 일어 인사)",
    )
    parser.add_argument("-u", "--url", default="http://127.0.0.1:9880", help="API Base URL")
    parser.add_argument("--no-stream", action="store_true", help="스트리밍 비활성화 (wav 전체)")
    parser.add_argument("-o", "--output", help="출력 파일 경로")
    parser.add_argument("-r", "--ref", help="참조 오디오 경로 (기본: sliced.list 첫 줄)")
    parser.add_argument("-pt", "--prompt-text", help="참조 오디오 텍스트")
    args = parser.parse_args()

    return test_tts(
        text=args.text,
        base_url=args.url.rstrip("/"),
        streaming=not args.no_stream,
        ref_path=args.ref,
        prompt_text=args.prompt_text,
        output_file=args.output,
    )


if __name__ == "__main__":
    sys.exit(main() or 0)
