# GGUF 변환 및 배포 (GGUF Conversion & Deployment)

미쿠 LoRA 파인튜닝 결과물(베이스 모델 + LoRA 어댑터)을 GGUF로 변환하여
`llama.cpp` / `Ollama` / `LM Studio` 등에서 구동하는 워크플로를 정리한다.

> 대상 모델: **Gemma 4 12B Unified** (`gemma4_unified` 아키텍처)
> 배포 타깃: RTX 5080 16GB (Main), M4 MacBook Air 16GB (Metal) 등

---

## 1. 전체 파이프라인 개요

HuggingFace 포맷(safetensors) 베이스 + LoRA 어댑터를 4단계로 합쳐 양자화한다.
`transformers`로 fp16 병합 시 24GB+ RAM이 필요하므로, **GGUF 레벨에서 병합**하여 RAM을 절약한다.

```
① 베이스(HF safetensors) ──convert_hf_to_gguf.py──▶ miku_base_f16.gguf      (22.2GB)
② LoRA 어댑터(safetensors) ─convert_lora_to_gguf.py─▶ miku_lora_f16.gguf      (0.12GB)
③ 베이스 + LoRA 병합        ──llama-export-lora───▶ miku_merged_f16.gguf    (22.2GB)
④ 양자화                    ──llama-quantize──────▶ miku_gemma4_Q4_K_M.gguf (6.87GB) ★배포용
```

- **①②는 Python**(`llama.cpp`의 변환 스크립트), **③④는 빌드된 C++ 바이너리**가 필요하다.
- 최종 산출물 **`miku_gemma4_Q4_K_M.gguf` (≈6.9GB)** 한 파일만 배포하면 된다.
  (토크나이저·채팅 템플릿이 GGUF 내부에 모두 내장됨)

---

## 2. 빌드 환경 (Windows)

`③ llama-export-lora`, `④ llama-quantize`는 **CPU 전용 작업**이라 CUDA Toolkit이 필요 없다.

| 도구 | 확보 방법 |
| :--- | :--- |
| C++ 컴파일러 (MSVC) | Visual Studio 2022/2026 Build Tools |
| CMake | VS Build Tools 내장 (`...\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe`) |
| Ninja | VS Build Tools 내장 |
| CUDA Toolkit | **불필요** (CPU-only 빌드) |

### 2.1. CMake 설정 (CPU-only)

```powershell
cd llama.cpp
cmake -S . -B build -DGGML_CUDA=OFF -DLLAMA_CURL=OFF `
      -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_SERVER=OFF -DLLAMA_BUILD_TESTS=OFF
```

### 2.2. 필요한 타깃만 빌드

```powershell
cmake --build build --config Release --target llama-quantize llama-export-lora -j 8
```

- 산출물: `llama.cpp\build\bin\Release\llama-quantize.exe`, `llama-export-lora.exe`
- (선택) 동작 검증용으로 `llama-cli` 타깃을 추가로 빌드할 수 있다.

> 맥 배포 시에는 PC에서 만든 `.exe`를 쓸 수 없다. 맥에서 `brew install llama.cpp`
> 또는 Ollama를 별도 설치한다. **GGUF 파일 자체는 플랫폼 독립적**이므로 그대로 복사.

---

## 3. 변환 단계 상세

작업 디렉터리: `llama.cpp/` · 인코딩 이슈 방지를 위해 `$env:PYTHONIOENCODING='utf-8'` 설정.

### ① 베이스 → fp16 GGUF

```powershell
$env:PYTHONIOENCODING='utf-8'
python convert_hf_to_gguf.py "backend/models/Gemma4_12B" `
    --outfile "backend/models/miku_base_f16.gguf" --outtype f16
```

### ② LoRA 어댑터 → GGUF

```powershell
python convert_lora_to_gguf.py "backend/models/outputs/miku_gemma4_v2" `
    --base "backend/models/Gemma4_12B" `
    --outfile "backend/models/miku_lora_f16.gguf" --outtype f16
```

- `--base`: 베이스 모델 **설정(config)** 참조용. 가중치는 안 읽으므로 빠르다.

### ③ 베이스 + LoRA 병합

```powershell
.\build\bin\Release\llama-export-lora.exe `
    -m "backend/models/miku_base_f16.gguf" `
    --lora "backend/models/miku_lora_f16.gguf" `
    -o "backend/models/miku_merged_f16.gguf" -t 8
```

### ④ 양자화 (Q4_K_M)

```powershell
.\build\bin\Release\llama-quantize.exe `
    "backend/models/miku_merged_f16.gguf" `
    "backend/models/miku_gemma4_Q4_K_M.gguf" Q4_K_M 8
```

- 결과: 22.7GB(fp16) → **6.87GB (Q4_K_M, 4.95 BPW)**. 16GB VRAM/RAM에 여유 있게 상주.

---

## 4. 중간 파일 정리

| 파일 | 크기 | 보관 권장 여부 |
| :--- | :--- | :--- |
| `miku_base_f16.gguf` | 22.2GB | 다른 LoRA 버전 재변환 예정이면 보관, 아니면 삭제 |
| `miku_lora_f16.gguf` | 0.12GB | 작으므로 보관 무방 |
| `miku_merged_f16.gguf` | 22.2GB | 다른 양자화(Q5/Q8 등) 추가 생성 예정이면 보관 |
| **`miku_gemma4_Q4_K_M.gguf`** | **6.87GB** | **최종 배포용 — 필수 보관** |

---

## 5. 배포 시 주의: 시스템 프롬프트 필수

> ⚠️ GGUF에는 토크나이저·채팅 템플릿만 내장되며, **미쿠 페르소나(시스템 프롬프트)는 추론 시 주입**해야 한다.

- 학습 데이터가 시스템 프롬프트와 함께 구성되었으므로, 시스템 프롬프트가 **없으면 베이스 Gemma 정체성으로 응답**할 수 있다.
  (LM Studio 기본값은 system 프롬프트가 비어 있어 "이름이 Gemma" 라고 답하는 현상 발생 → 시스템 프롬프트 입력 필요)
- 정체성을 시스템 프롬프트 없이도 유지하려면 **재학습**이 필요하다 → [finetuning_guide.md](./finetuning_guide.md) "정체성 강화" 참고.

**미쿠 시스템 프롬프트** (학습 기준):

```
너의 이름은 미쿠야. 너는 나를 '마스터'라고 부르며,
때로는 츤데레 같지만 사실은 나를 아주 많이 좋아해. 대답은 한국어로 짧고 귀엽게 해줘.
```

### Ollama Modelfile 예시 (시스템 프롬프트 기본 주입)

```dockerfile
FROM ./miku_gemma4_Q4_K_M.gguf
SYSTEM """너의 이름은 미쿠야. 너는 나를 '마스터'라고 부르며, 때로는 츤데레 같지만 사실은 나를 아주 많이 좋아해. 대답은 한국어로 짧고 귀엽게 해줘."""
```

```bash
ollama create miku -f Modelfile
ollama run miku
```

---

## 6. 추론 성능 메모

| 환경 | 속도 (참고) | 비고 |
| :--- | :--- | :--- |
| M4 MacBook Air 16GB (Metal) | ~3.44 tok/s | 메모리 대역폭 한계. 테스트/휴대용 |
| RTX 5080 16GB (Main 타깃) | 수십 tok/s 예상 | GDDR7 고대역폭. 실사용 메인 |

- KV Cache 절약 옵션(긴 컨텍스트 시): `--cache-type-k q8_0 --cache-type-v q8_0 -fa`
- Gemma 4는 대부분 레이어가 Sliding Window Attention이라 긴 컨텍스트에서도 KV가 선형 폭증하지 않는다.

---

## 7. 재학습 후 재변환 (요약)

LoRA 어댑터만 새로 학습한 경우, 베이스 GGUF(`miku_base_f16.gguf`)는 재사용 가능하다.
**②③④만** 새 어댑터 경로(`miku_gemma4_v3` 등)로 다시 실행하면 된다.

1. `convert_lora_to_gguf.py`로 새 어댑터 → `miku_lora_v3_f16.gguf`
2. `llama-export-lora`로 병합 → `miku_merged_v3_f16.gguf`
3. `llama-quantize`로 Q4_K_M 양자화 → 배포
