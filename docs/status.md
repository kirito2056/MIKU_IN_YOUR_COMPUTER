# MIKU IN YOUR COMPUTER - 프로젝트 현황 (Status)

이 문서는 `docs/` 폴더에 정의된 기획/설계와 실제 구현된 코드베이스 간의 진행 상황을 비교하고 추적하기 위한 문서입니다.

**프론트엔드 실행 환경**: Node.js 24.14.0, `npm install --legacy-peer-deps` 필요. `npm run dev` (Vite) + `npm run electron:start` (Electron) 동시 실행.

## 📊 전체 진행률 요약

- **Phase 1 (Foundation)**: ~65% 진행 — 백엔드/프론트 실시간 파이프라인(WS 스트리밍 + TTS) 완성
- **Phase 2 (Intelligence & Personality)**: ~55% 진행 — LoRA 파인튜닝 수행 + GGUF 배포 파이프라인 확립
- **Phase 3 (Body & Presence)**: ~75% 진행 — 3D/모션/립싱크/음성 재생 완성
- **Phase 4 (Memory & Context)**: ~10% 진행 — DB 스키마 초안 + Docker 실행 환경만 존재

---

## 🏗️ 모듈별 상세 구현 현황

### 1. Backend Core (The Nervous System)
- [x] **FastAPI 뼈대 구축**: `main.py`에 REST(`/api/chat`, `/api/tts/*`) 및 WebSocket(`/ws/chat`) 엔드포인트 구현 완료
- [x] **LLM WebSocket 스트리밍**: 토큰 단위 `stream_chunk` 전송 + 완료 후 TTS 오디오 base64 청크 전송 파이프라인 완료 (2026-05-29)
- [x] **CORS 및 기본 라우팅**: 프론트엔드 연동을 위한 설정 완료
- [ ] **에러 핸들링 및 로깅**: 기획서 수준의 체계적 로깅 아키텍처 미구현
- [ ] **멀티프로세스 아키텍처**: AI 모델별(LLM, Vision, TTS) 프로세스 격리 미구현

### 2. LLM / 추론 엔진 (The Brain)
- [x] **모델 확보**: Gemma 4 12B(`gemma4_unified`)로 전환 완료 (2026-06, Gemma 3에서 마이그레이션)
- [x] **기본 추론**: `services/llm_service.py` — HuggingFace `transformers` + 4-bit 양자화 + 스트리밍(`TextIteratorStreamer`) 구현 완료
- [x] **GGUF 배포 파이프라인**: 베이스→GGUF 변환, LoRA 병합(`llama-export-lora`), Q4_K_M 양자화(6.87GB)까지 확립. LM Studio(Windows)/Mac(Metal) 구동 확인 → `docs/ai/gguf_deployment.md`
- [x] **런타임 모델 경로 정리**: 기본값을 베이스(`models/Gemma4_12B`) + LoRA v4(`models/outputs/miku_gemma4_v4`)로 통일 — 백엔드 기동 시 파인튜닝 모델 자동 로드 (env `LLM_MODEL_PATH`/`LORA_PATH`로 오버라이드, `LORA_PATH=""`면 베이스만). ※ `models/miku_12B_merged`는 구 Gemma 3 병합본(레거시)
- [ ] **추론 엔진 결정**: 백엔드 서빙을 transformers 유지 vs llama.cpp(GGUF) 전환할지 결정 필요 (기존 ExLlamaV2 계획은 GGUF 파이프라인으로 사실상 대체)

### 3. 모델 파인튜닝 (Personality)
- [x] **데이터셋 구축 파이프라인**: 상황별 9카테고리 × (chat/multiturn/paraphrased), 합성·패러프레이즈·반복제한(`cap_repetition`)·자연화(`naturalize_chat_data`) 스크립트 완비
- [x] **LoRA 학습 수행**: `train_lora_gemma4.py`(QLoRA)로 실제 학습 완료 — `models/outputs/miku_gemma4_v1`~`v4` 산출 (2026-06)
- [x] **병합·양자화**: `merge_lora.py` Gemma4 지원 + GGUF 변환·Q4_K_M 양자화 완료
- [x] **정체성 검증 (v4)**: 성격 테스트 통과 (2026-07-12) — 시스템 프롬프트 **없이도** 미쿠 정체성 유지, "너 Gemma야?/구글이 만들었지?/Are you Gemma?" 전부 부정하고 미쿠로 응답. adversarial 데이터는 v4 학습에 미포함이었으나 `system_prompt_ratio 0.5`만으로 목표 달성
- [ ] **(선택) v5 재학습**: adversarial + naturalize 데이터 반영 시 응답 다양성 개선 여지 (현재 v4는 학습 데이터 문장을 거의 그대로 재현하는 경향)
- [ ] **백엔드 실기동 검증**: FastAPI 서버 기동 → WebSocket 대화로 end-to-end 확인 필요 (모델+어댑터 조합 자체는 검증 완료)

### 4. 음성 합성 (The Voice - GPT-SoVITS)
- [x] **엔진 테스트**: `scripts/test_tts_stream.py` 작성 및 WebUI를 통한 동작 확인 완료
- [x] **Backend 연동**: `services/tts_service.py` — LLM 응답 → TTS 합성 → WebSocket base64 청크 스트리밍 완료 (2026-05-29)
- [ ] **감정 모델링**: 텍스트 컨텍스트에 따른 음성 톤/감정 동적 변화 로직 미구현

### 5. Frontend (The Body)
- [x] **Electron 기반 환경**: 투명 윈도우, 화면 전체 해상도 적용, `workAreaSize` 동적 감지, 클릭 통과(Click-through) 설정 완료
- [x] **3D 렌더링**: Three.js (@react-three/fiber, @pixiv/three-vrm) 기반 VRM 로딩, VRMA 모션 1~7 랜덤 재생 + Crossfade, 숨쉬기/눈 깜빡임/마우스 트래킹 완료
- [x] **대화형 UI + WebSocket 연동**: `ChatPanel` + `useChatWebSocket` — 스트리밍 채팅 표시 완료 (2026-05-29)
- [x] **오디오 재생 + 립싱크**: TTS 오디오 재생(`playAudio.ts`) + 립싱크/말하기 모션 연동(`lipSync.ts`) 완료 (2026-05-29)
- [ ] **Spatial Audio**: Web Audio API PannerNode 기반 공간 음향 미구현

### 6. Memory & Database
- [x] **스키마 초안**: PostgreSQL 17 + pgvector 스키마(`db/schema/001`~`011`) + `apply_schema.py` 작성 완료 (2026-05-30)
- [x] **로컬 DB 실행 환경**: `docker-compose.yml` + `scripts/dev_db.py` 구성 완료
- [ ] **장/단기 기억 시스템**: 벡터 검색 및 RAG 파이프라인, 백엔드 연동 미구현

### 7. Vision / Hardware (The Eyes)
- [ ] **카메라 연동**: OpenCV 기반 사용자 얼굴/모션 트래킹 미구현
- [ ] **멀티모달 이해**: Gemma 4 Vision 연동 미구현

---

## 🎯 다음 마일스톤 (추천 작업)

1. ~~**3D VRM 모델 로딩**~~ ✅ 완료 (2026-03-10, 모션 Crossfade 2026-03-12)
2. ~~**대화형 UI + 백엔드 WebSocket 연동**~~ ✅ 완료 (2026-05-29)
3. ~~**TTS 백엔드 파이프라인 통합 + 립싱크**~~ ✅ 완료 (2026-05-29)
4. ~~**파인튜닝 (LoRA) 진행**~~ ✅ 완료 (2026-06, v1~v4 + GGUF 양자화)
5. **파인튜닝 모델 런타임 연동**
   - ~~백엔드 기본 모델을 파인튜닝 모델로 통일 (경로 불일치 정리)~~ ✅ 완료 (2026-07-12, 베이스 + LoRA v4)
   - transformers 유지 vs llama.cpp(GGUF) 서빙 전환 결정
   - 백엔드 기동 후 실대화로 미쿠 정체성 응답 검증
6. **정체성 강화 재학습 (v5)**
   - adversarial·naturalize 데이터 반영 → 시스템 프롬프트 없이도 미쿠 정체성 유지
   - 재변환은 `docs/ai/gguf_deployment.md` §7 (②③④만 재실행)
7. **기억 시스템 (Phase 4 착수)**
   - Docker DB 구동 + 스키마 적용 → 대화 로그 저장 → pgvector 기반 RAG 연동
8. **감정 모델링**
   - LLM 응답의 감정 태그 → TTS 톤/모션 매핑

*Last Updated: 2026-07-12*
