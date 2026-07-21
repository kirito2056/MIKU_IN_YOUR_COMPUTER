"""
llama.cpp 서버 기반 LLM 서비스
로컬 llama-server(OpenAI 호환 API)를 호출해 추론합니다.
서버가 떠 있지 않으면 GGUF 모델로 자동 기동합니다.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Iterator, List, Dict, Optional

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = Path(__file__).resolve().parent.parent


def _find_server_exe() -> Optional[Path]:
    """llama-server 실행파일 탐색: 프로젝트 내 빌드 → PATH (맥/리눅스는 brew 등으로 설치)"""
    local = PROJECT_ROOT / "llama.cpp" / "release-cuda" / "llama-server.exe"
    if local.exists():
        return local
    on_path = shutil.which("llama-server")
    return Path(on_path) if on_path else None

MIKU_SYSTEM_PROMPT = (
    "너의 이름은 미쿠야. 너는 나를 '마스터'라고 부르며, "
    "때로는 츤데레 같지만 사실은 나를 아주 많이 좋아해. "
    "대답은 한국어로 짧고 귀엽게 해줘."
)

DEFAULT_SERVER_URL = "http://127.0.0.1:8080"
DEFAULT_GGUF_PATH = "models/miku_gemma4_v5_Q4_K_M.gguf"


class LlamaCppServiceError(Exception):
    """llama-server 호출 실패"""


class LlamaCppService:
    """llama-server HTTP API를 사용하는 LLM 서비스 (LLMService와 동일 인터페이스)"""

    def __init__(
        self,
        server_url: str = DEFAULT_SERVER_URL,
        gguf_path: str = DEFAULT_GGUF_PATH,
        server_exe: Optional[str] = None,
        ctx_size: int = 4096,
        n_gpu_layers: int = 99,
        autostart: bool = True,
        startup_timeout: float = 120.0,
    ):
        self.server_url = server_url.rstrip("/")
        self.gguf_path = self._resolve_path(gguf_path)
        self.server_exe = Path(server_exe) if server_exe else _find_server_exe()
        self.ctx_size = ctx_size
        self.n_gpu_layers = n_gpu_layers
        self.startup_timeout = startup_timeout
        self._proc: Optional[subprocess.Popen] = None
        self._is_loaded = False

        if self._health_ok():
            print(f"✅ llama-server 연결됨: {self.server_url}")
            self._is_loaded = True
        elif autostart:
            self._start_server()

    @staticmethod
    def _resolve_path(path: str) -> Path:
        p = Path(path)
        return p if p.is_absolute() else BACKEND_DIR / p

    def _health_ok(self) -> bool:
        try:
            r = requests.get(f"{self.server_url}/health", timeout=2)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def _start_server(self) -> None:
        """llama-server 자동 기동 후 health 대기"""
        if self.server_exe is None or not self.server_exe.exists():
            raise LlamaCppServiceError(
                "llama-server 실행파일을 찾을 수 없습니다 (LLAMA_SERVER_EXE env 또는 PATH 확인)"
            )
        if not self.gguf_path.exists():
            raise LlamaCppServiceError(f"GGUF 모델이 없습니다: {self.gguf_path}")

        port = self.server_url.rsplit(":", 1)[-1]
        cmd = [
            str(self.server_exe),
            "-m", str(self.gguf_path),
            "--host", "127.0.0.1",
            "--port", port,
            "-ngl", str(self.n_gpu_layers),
            "-c", str(self.ctx_size),
            "--no-webui",
        ]
        print(f"🚀 llama-server 기동 중: {self.gguf_path.name} (port {port})")
        log_path = BACKEND_DIR / "llama_server.log"
        self._log_file = open(log_path, "a", encoding="utf-8")
        self._proc = subprocess.Popen(
            cmd,
            stdout=self._log_file,
            stderr=subprocess.STDOUT,
            cwd=str(PROJECT_ROOT),
        )

        deadline = time.time() + self.startup_timeout
        while time.time() < deadline:
            if self._proc.poll() is not None:
                raise LlamaCppServiceError(
                    f"llama-server가 종료됨 (exit {self._proc.returncode}). 로그: {log_path}"
                )
            if self._health_ok():
                self._is_loaded = True
                print(f"✅ llama-server 준비 완료: {self.server_url}")
                return
            time.sleep(0.5)
        raise LlamaCppServiceError(f"llama-server 기동 타임아웃 ({self.startup_timeout}s)")

    @staticmethod
    def _build_messages(user_message: str) -> List[Dict[str, str]]:
        return [
            {"role": "system", "content": MIKU_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

    def chat(
        self,
        user_message: str,
        max_new_tokens: int = 200,
        temperature: float = 0.7,
        top_p: float = 0.9,
        **kwargs,
    ) -> str:
        """단발 응답 생성"""
        try:
            r = requests.post(
                f"{self.server_url}/v1/chat/completions",
                json={
                    "messages": self._build_messages(user_message),
                    "max_tokens": max_new_tokens,
                    "temperature": temperature,
                    "top_p": top_p,
                },
                timeout=300,
            )
            r.raise_for_status()
        except requests.RequestException as e:
            raise LlamaCppServiceError(f"llama-server 요청 실패: {e}") from e
        return r.json()["choices"][0]["message"]["content"].strip()

    def chat_stream(
        self,
        user_message: str,
        max_new_tokens: int = 200,
        temperature: float = 0.7,
        top_p: float = 0.9,
        **kwargs,
    ) -> Iterator[str]:
        """토큰 단위 스트리밍 응답 생성 (SSE)"""
        try:
            r = requests.post(
                f"{self.server_url}/v1/chat/completions",
                json={
                    "messages": self._build_messages(user_message),
                    "max_tokens": max_new_tokens,
                    "temperature": temperature,
                    "top_p": top_p,
                    "stream": True,
                },
                stream=True,
                timeout=300,
            )
            r.raise_for_status()
            for raw in r.iter_lines():
                # SSE 응답에 charset이 없으면 requests가 latin-1로 잘못 디코딩하므로 직접 UTF-8 처리
                line = raw.decode("utf-8") if raw else ""
                if not line.startswith("data: "):
                    continue
                payload = line[len("data: "):]
                if payload == "[DONE]":
                    break
                delta = json.loads(payload)["choices"][0].get("delta", {})
                content = delta.get("content")
                if content:
                    yield content
        except requests.RequestException as e:
            raise LlamaCppServiceError(f"llama-server 스트리밍 실패: {e}") from e

    def unload_model(self) -> None:
        """자동 기동한 서버 프로세스 종료 (외부 서버는 건드리지 않음)"""
        if self._proc is not None and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._proc.kill()
            print("✅ llama-server 종료 완료")
        self._proc = None
        self._is_loaded = False


# 전역 서비스 인스턴스 (싱글톤)
_llamacpp_service: Optional[LlamaCppService] = None


def get_llamacpp_service(**kwargs) -> LlamaCppService:
    global _llamacpp_service
    if _llamacpp_service is None:
        _llamacpp_service = LlamaCppService(
            server_url=os.getenv("LLAMA_SERVER_URL", DEFAULT_SERVER_URL),
            gguf_path=os.getenv("LLAMA_GGUF_PATH", DEFAULT_GGUF_PATH),
            server_exe=os.getenv("LLAMA_SERVER_EXE") or None,
            ctx_size=int(os.getenv("LLAMA_CTX_SIZE", "4096")),
            n_gpu_layers=int(os.getenv("LLAMA_NGL", "99")),
            **kwargs,
        )
    return _llamacpp_service
