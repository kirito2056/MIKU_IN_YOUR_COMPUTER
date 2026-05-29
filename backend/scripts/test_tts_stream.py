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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.tts_service import TTSService, TTSServiceError, get_tts_service

ROOT = Path(__file__).resolve().parent.parent.parent


def test_tts(
    text: str,
    base_url: str = "http://127.0.0.1:9880",
    streaming: bool = True,
    ref_path: str = None,
    prompt_text: str = None,
    output_file: str = None,
):
    service = TTSService(
        base_url=base_url.rstrip("/"),
        ref_wav_path=ref_path,
        prompt_text=prompt_text,
    )

    if not service.is_configured():
        print("⚠️ 참조 음원을 찾을 수 없습니다. voice/datasets/asr/sliced.list 확인")
        return 1

    ref_path_resolved, _ = service.resolve_ref()
    print(f"📡 요청: {service.base_url}/")
    print(f"   텍스트: {text[:50]}{'...' if len(text) > 50 else ''}")
    print(f"   참조: {Path(ref_path_resolved).name}")
    print(f"   스트리밍: {streaming}")
    print()

    try:
        chunks = []
        total = 0
        for chunk in service.synthesize_stream(text):
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
            out_path = ROOT / "output" / f"tts_test.{ext}"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "wb") as f:
            f.write(audio_data)
        print(f"   저장: {out_path}")
        if out_path.suffix.lower() in (".ogg", ".wav"):
            print("   재생: 윈도우에서 더블클릭 또는 media player로 열기")
        return 0

    except TTSServiceError as e:
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
