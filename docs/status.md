# MIKU IN YOUR COMPUTER - 프로젝트 현황 (Status)

이 문서는 `docs/` 폴더에 정의된 기획/설계와 실제 구현된 코드베이스 간의 진행 상황을 비교하고 추적하기 위한 문서입니다.

**프론트엔드 실행 환경**: Node.js 24.14.0, `npm install --legacy-peer-deps` 필요. `npm run dev` (Vite) + `npm run electron:start` (Electron) 동시 실행.

## 📊 전체 진행률 요약

- **Phase 1 (Foundation)**: ~30% 진행
- **Phase 2 (Intelligence & Personality)**: ~10% 진행
- **Phase 3 (Body & Presence)**: ~55% 진행
- **Phase 4 (Memory & Context)**: 0% 진행

---

## 🏗️ 모듈별 상세 구현 현황

### 1. Backend Core (The Nervous System)
- [x] **FastAPI 뼈대 구축**: `main.py`에 기본 REST 및 WebSocket 엔드포인트 구현 완료
- [x] **CORS 및 기본 라우팅**: 프론트엔드 연동을 위한 설정 완료
- [ ] **에러 핸들링 및 로깅**: 기획서 수준의 체계적 로깅 아키텍처 미구현
- [ ] **멀티프로세스 아키텍처**: AI 모델별(LLM, Vision, TTS) 프로세스 격리 미구현

### 2. LLM / 추론 엔진 (The Brain)
- [x] **모델 다운로드**: 로컬 환경에 모델 가중치 파일 다운로드 완료
- [x] **기본 추론 스크립트**: `services/llm_service.py`를 통해 HuggingFace `transformers` + 4-bit 양자화 방식 구현 완료
- [ ] **ExLlamaV2 마이그레이션**: 기획된 최고 성능 확보를 위한 프레임워크 전환 필요
- [ ] **성능 최적화**: vRAM 관리, 캐싱 전략 등 미구현

### 3. 모델 파인튜닝 (Personality)
- [x] **데이터셋 구축 파이프라인**: `backend/finetuning/` 폴더 내 병합/생성 스크립트 작성 완료 (`miku_personality_*.json` 등)
- [ ] **실제 파인튜닝 (LoRA 학습)**: ⚠️ **진행 예정** (스크립트만 존재, 실제 학습은 아직 수행되지 않음)
- [ ] **추론 엔진 연동 검증**: 학습된 어댑터를 런타임에 동적으로 로딩하여 테스트 필요

### 4. 음성 합성 (The Voice - GPT-SoVITS)
- [x] **엔진 테스트**: `scripts/test_tts_stream.py` 작성 및 WebUI를 통한 동작 확인 완료
- [ ] **Backend 연동**: LLM 응답을 스트리밍으로 받아 실시간으로 TTS 생성 및 오디오 스트림 전송 파이프라인 미구현
- [ ] **감정 모델링**: 텍스트 컨텍스트에 따른 음성 톤/감정 동적 변화 로직 미구현

### 5. Frontend (The Body)
- [x] **Electron 기반 환경**: 투명 윈도우, 화면 전체 해상도(3440x1440) 적용, `workAreaSize` 동적 감지, 클릭 통과(Click-through) 설정 완료
- [x] **UI 컴포넌트**: React + Vite + Zustand 의존성 설치 완료. Miku 3D Model Area(960×1440px, 우측 정렬), 대화창(400px, 폰트 20~24px) 레이아웃 구현 완료
- [x] **3D 렌더링**: Three.js (@react-three/fiber, @pixiv/three-vrm) 기반 VRM 모델 로딩 및 아바타 렌더링 구현 완료 (`Scene3D.tsx`, `MikuModel.tsx`, `miku_v1.vrm`)
- [ ] **오디오 재생**: Web Audio API (Spatial PannerNode) 미구현

### 6. Memory & Database
- [ ] **데이터베이스 셋업**: PostgreSQL 17+ 구동 환경 미구현
- [ ] **장/단기 기억 시스템**: `pgvector` 기반 벡터 검색 및 RAG 파이프라인 미구현

### 7. Vision / Hardware (The Eyes)
- [ ] **카메라 연동**: OpenCV 기반 사용자 얼굴/모션 트래킹 미구현
- [ ] **멀티모달 이해**: Gemma Vision 기반 화면 및 현실 상황 인지 미구현

---

## 🎯 다음 마일스톤 (추천 작업)

1. ~~**3D VRM 모델 로딩**~~ ✅ 완료 (2026-03-10)
   - `frontend/public/models/miku_v1.vrm` 배치, `Scene3D`/`MikuModel` 컴포넌트로 실제 미쿠 3D 모델 렌더링
   - VRMA 모션 1~7번 랜덤 연속 재생 및 자연스러운 트랜지션(Crossfade) 적용 완료 (2026-03-12)
2. **대화형 UI 구성 및 백엔드 WebSocket 연동**
   - 현재 프론트엔드 대화창에 사용자 입력을 받을 수 있는 Input 필드 추가
   - FastAPI `/ws/chat` 엔드포인트와 연결하여 대화창에 실시간 채팅 응답 표시
3. **TTS 백엔드 파이프라인 통합**
   - WebUI로 테스트 완료한 GPT-SoVITS를 FastAPI 내부로 가져와 텍스트(LLM) -> 음성(TTS) 플로우 완성
4. **LLM 성능 극대화 (ExLlamaV2 도입)**
   - 파인튜닝 전, 베이스 모델이 실시간 대화가 가능하도록 추론 엔진 최적화
5. **파인튜닝 (LoRA) 진행 및 검증**
   - 만들어진 데이터셋을 활용해 실제로 모델을 학습하고 억양과 성격(Personality) 부여

*Last Updated: 2026-03-12*
