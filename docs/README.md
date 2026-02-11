# MIKU IN YOUR COMPUTER - Documentation

이 프로젝트는 데스크톱에 상주하며 사용자와 교감하고 성장하는 AI 컴패니언, **Hatsune Miku**를 구현하기 위한 문서 저장소입니다.

## 📂 문서 구조

| 폴더 | 설명 | 주요 내용 |
|------|------|-----------|
| **[planning](./planning/)** | **기획 & 설계** | 프로젝트 개요, 성격 정의, 전체 아키텍처, 하드웨어 전략, 버전 관리, 세부 결정 사항 |
| **[ai](./ai/)** | **AI 파이프라인** | Gemma 3(LLM), 비전, 음성, 학습 로직, 비상장치 |
| **[frontend](./frontend/)** | **클라이언트 (UI)** | Electron 오버레이, 3D 애니메이션(SAO/의자춤), 연출 |
| **[backend](./backend/)** | **서버 & DB** | FastAPI 명세, DB 스키마(기억/지식그래프), 에러 로깅, 모니터링, 테스트 전략, 개발 도구, 벡터 검색 최적화, 성능 최적화 |
| **[plugins](./plugins/)** | **플러그인** | 확장 시스템 아키텍처, SDK |
| **[deployment](./deployment/)** | **배포 & 환경** | 로컬 설치 가이드, 하드웨어 요구사항 |
| **[i18n](./i18n/)** | **국제화** | 다국어 지원 구조 (EN/KO/JA) |

---

*Last Updated: 2026-02-08*

## 📝 최근 추가 문서

- **벡터 검색 최적화** (`backend/vector_search_optimization.md`): pgvector 인덱스 전략, 검색 알고리즘, 성능 최적화
- **성능 최적화 전략** (`backend/performance_optimization.md`): 캐싱, 배치 처리, GPU 관리, 쿼리 최적화
