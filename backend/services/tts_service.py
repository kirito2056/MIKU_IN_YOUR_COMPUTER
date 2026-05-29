"""
GPT-SoVITS TTS 서비스
외부 api.py 서버(http://127.0.0.1:9880)를 호출해 음성을 합성합니다.
"""
from __future__ import annotations

import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Iterator, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VOICE_ROOT = PROJECT_ROOT / "voice" / "datasets"
SLICED_LIST = VOICE_ROOT / "asr" / "sliced.list"


class TTSServiceError(Exception):
    """TTS API 호출 실패"""


def get_default_ref() -> Tuple[Optional[str], Optional[str]]:
    """sliced.list에서 첫 번째 참조 음원 경로·텍스트."""
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


class TTSService:
    """GPT-SoVITS API 클라이언트."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:9880",
        ref_wav_path: Optional[str] = None,
        prompt_text: Optional[str] = None,
        text_language: str = "ja",
        prompt_language: str = "ja",
        timeout: float = 120.0,
        chunk_size: int = 8192,
    ):
        self.base_url = base_url.rstrip("/")
        self.ref_wav_path = ref_wav_path
        self.prompt_text = prompt_text
        self.text_language = text_language
        self.prompt_language = prompt_language
        self.timeout = timeout
        self.chunk_size = chunk_size

    @classmethod
    def from_env(cls) -> "TTSService":
        return cls(
            base_url=os.getenv("TTS_API_URL", "http://127.0.0.1:9880"),
            ref_wav_path=os.getenv("TTS_REF_WAV_PATH") or None,
            prompt_text=os.getenv("TTS_PROMPT_TEXT") or None,
            text_language=os.getenv("TTS_TEXT_LANGUAGE", "ja"),
            prompt_language=os.getenv("TTS_PROMPT_LANGUAGE", "ja"),
            timeout=float(os.getenv("TTS_TIMEOUT", "120")),
        )

    def resolve_ref(self) -> Tuple[str, str]:
        ref_path = self.ref_wav_path or ""
        prompt_text = self.prompt_text or ""
        if not ref_path or not prompt_text:
            default_path, default_text = get_default_ref()
            ref_path = ref_path or (default_path or "")
            prompt_text = prompt_text or (default_text or "")
        if not ref_path:
            raise TTSServiceError(
                "참조 음원이 없습니다. TTS_REF_WAV_PATH 또는 voice/datasets/asr/sliced.list 확인"
            )
        return ref_path, prompt_text

    def is_configured(self) -> bool:
        try:
            self.resolve_ref()
            return True
        except TTSServiceError:
            return False

    def build_request_url(self, text: str) -> str:
        ref_path, prompt_text = self.resolve_ref()
        params = {
            "text": text,
            "text_language": self.text_language,
            "refer_wav_path": ref_path,
            "prompt_text": prompt_text,
            "prompt_language": self.prompt_language,
        }
        return f"{self.base_url}/?{urllib.parse.urlencode(params)}"

    def check_api_reachable(self) -> bool:
        """GPT-SoVITS API 서버 연결 가능 여부 (파라미터 없이 접속)."""
        try:
            req = urllib.request.Request(self.base_url + "/")
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status < 500
        except urllib.error.HTTPError as e:
            # 파라미터 없는 요청은 4xx일 수 있으나 서버는 살아 있음
            return e.code < 500
        except Exception:
            return False

    def health_status(self) -> dict:
        ref_ok = self.is_configured()
        api_ok = self.check_api_reachable() if ref_ok else False
        ref_path, _ = (self.resolve_ref() if ref_ok else (None, None))
        return {
            "configured": ref_ok,
            "api_reachable": api_ok,
            "ready": ref_ok and api_ok,
            "api_url": self.base_url,
            "ref_wav": ref_path,
        }

    def synthesize_stream(self, text: str) -> Iterator[bytes]:
        """GPT-SoVITS 스트리밍 응답을 청크 단위로 yield."""
        text = text.strip()
        if not text:
            raise TTSServiceError("합성할 텍스트가 비어 있습니다.")

        url = self.build_request_url(text)
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status != 200:
                    body = resp.read().decode("utf-8", errors="replace")
                    raise TTSServiceError(f"TTS API 오류 {resp.status}: {body[:300]}")
                while True:
                    chunk = resp.read(self.chunk_size)
                    if not chunk:
                        break
                    yield chunk
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace") if e.fp else str(e)
            raise TTSServiceError(f"TTS HTTP 오류 {e.code}: {body[:300]}") from e
        except TTSServiceError:
            raise
        except Exception as e:
            raise TTSServiceError(
                f"TTS API 연결 실패 ({self.base_url}). api.py 서버 실행 여부 확인."
            ) from e

    def synthesize(self, text: str) -> bytes:
        return b"".join(self.synthesize_stream(text))


_tts_service: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService.from_env()
    return _tts_service
