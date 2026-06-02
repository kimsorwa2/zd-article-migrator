# zd-article-migrator 구현 TODO

프로젝트 진행 상황을 체크박스로 관리하기 위한 문서입니다.  
완료 시 `[ ]`를 `[x]`로 바꾸고, 필요하면 메모를 남겨주세요.

---

## 자주 쓰는 기본 명령어

### 1) DB 연결/마이그레이션 반영 (백엔드)

```powershell
cd C:\Users\kimso\Documents\workspace\demo\zd-article-migrator\backend
.\.venv\Scripts\Activate.ps1
python -m alembic upgrade head
python -m alembic current
```

- `upgrade head`: 최신 마이그레이션까지 DB 스키마 반영 (현재 head: `0013_ai_ocr_prompt_templates`)
- `current`: 현재 DB에 반영된 리비전 확인
- 참고: PowerShell에서 `alembic` 명령이 안 잡히면 `python -m alembic ...` 형태를 사용

### 2) 백엔드 서버 실행

```powershell
cd C:\Users\kimso\Documents\workspace\demo\zd-article-migrator\backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- 기본 접속 주소: `http://localhost:8000`
- 헬스체크: `http://localhost:8000/api/health`

### 3) 프론트엔드 서버 실행

```powershell
cd C:\Users\kimso\Documents\workspace\demo\zd-article-migrator\frontend
npm install
npm run dev
```

- 기본 접속 주소: `http://localhost:5173`
- 최초 1회 또는 의존성 변경 시 `npm install` 실행

---

## 0) 프로젝트 초기 세팅

- [x] `backend/`, `frontend/` 디렉토리 구조 생성
- [x] `backend/requirements.txt` 작성
- [x] `frontend/package.json`, `frontend/vite.config.ts` 작성
- [x] `backend/db/models.py` 모델 정의
  - [x] `instances`, `brands`, `categories`, `sections`, `articles`, `migration_mappings`
  - [x] AI OCR: `ai_ocr_settings`, `ai_ocr_analysis_history`, `ai_ocr_prompt_templates` (Alembic 0007~0013)
- [x] `backend/db/database.py` 비동기 DB 연결 설정
- [x] Alembic 초기 구성 + 리비전 `0001` ~ `0013`
- [x] `backend/main.py` FastAPI 기본 설정 + 라우터 등록
- [x] `backend/.env.example` 작성
- [x] Neon 연결 및 `alembic current` 정상 확인
- [ ] 로컬/배포 환경별 `alembic upgrade head` 반영 여부 주기적 확인

---

## 1) 백엔드 공통 기반 정리

- [ ] `backend/core/config.py` 생성
  - [ ] 환경변수 로딩/검증 로직 통합
  - [ ] 앱 전역 설정 객체 제공
- [ ] 공통 에러 응답 포맷 정의
- [ ] 공통 로깅 포맷/레벨 정리
- [ ] DB 세션 의존성 사용 가이드 정리

---

## 2) Zendesk 클라이언트 계층

- [x] `services/zendesk_client.py` 기본 구현
  - [x] Basic Auth 헤더 생성
  - [x] 공통 GET/POST/PUT/PATCH/DELETE 메서드
  - [x] 요청 간 지연(0.5초) 적용
  - [x] 429 응답 시 `Retry-After` 기반 재시도(최대 3회)
  - [x] JSON 파싱 실패 → `ZendeskClientError` (수집 경고 처리용)

---

## 3) 인스턴스 관리 API

- [x] `api/schemas.py`에 인스턴스/브랜드 관련 스키마 추가
- [x] `api/routers/instances.py` CRUD 구현
  - [x] 통합 인스턴스 생성 (`POST /api/instances`)
  - [x] 인스턴스 목록/상세 조회
  - [x] 인스턴스 수정·활성/비활성 전환
  - [x] 인스턴스 삭제 (`DELETE /api/instances/{id}`, CASCADE, 수집 중 409)
- [x] 등록 시 브랜드 미리보기·선택 저장
- [x] 연결 테스트 API (`POST /api/instances/{id}/connection-test`)

---

## 4) 데이터 수집 (Zendesk → DB)

- [x] `services/fetch_service.py` 구현
  - [x] 브랜드별 카테고리/섹션/아티클 수집·업서트
  - [x] 아티클 **커서 페이지네이션** (`page[size]=100`, `links.next` / `meta.has_more`)
  - [x] 수집 완료 시 `instances.last_fetched_at` 갱신
  - [x] `_sync_one_brand` 분리 → **브랜드 단건 수집** (`sync_source_brand`)
- [x] 백그라운드 수집 + 진행률
  - [x] `services/fetch_progress.py` (`FetchProgressTracker`, `warnings` 목록)
  - [x] `services/fetch_sync_job.py` (전체/브랜드 `brand_id` 옵션)
  - [x] `POST /api/fetch/{instance_id}/sync` → **202**
  - [x] `POST /api/fetch/{instance_id}/brands/{brand_id}/sync` → **202**
  - [x] `GET /api/fetch/{instance_id}/sync/progress` (폴링)
- [x] `GET /api/fetch/{instance_id}/detail` (트리 UI용 상세)
- [x] 첨부 API 일부 실패 시 경고만 기록하고 수집 계속
- [x] 프론트: `InstancesPage` 전체/브랜드 수집, `FetchDataTree` 「이 브랜드 수집」, `SyncProgressPanel` 경고·실패 후 패널 유지

---

## 5) 마이그레이션 실행 (소스 → 타겟)

- [x] `services/migration_service.py`
  - [x] 브랜드 → 타겟 **카테고리** (이름 기준 매핑/생성)
  - [x] 소스 카테고리 → 타겟 **상위 섹션**
  - [x] 소스 섹션 → 타겟 **하위 섹션** (`parent_section_id`)
  - [x] 아티클 생성/업데이트 + 첨부·본문 URL 치환
  - [x] 중복 정책 `skip` / `update` / `force`
  - [x] 타겟 Help Center **locale 정규화** (`_normalize_help_center_locale`, `locales.json` 조회)
  - [x] 타겟 Help Center **브랜드 서브도메인** (`target_brand_id`)
- [x] `migration_mappings` 생성·갱신
- [x] 백그라운드 마이그레이션 + 진행률
  - [x] `services/migrate_progress.py`, `services/migrate_sync_job.py`
  - [x] `POST /api/migrate/execute` → **202**
  - [x] `GET /api/migrate/progress?source_instance_id=&target_instance_id=`
- [x] `GET /api/migrate/tree`, `GET /api/migrate/overlay`, `GET /api/migrate/target-tree`
- [x] `DELETE /api/migrate/mappings` (매핑 기록 일괄 삭제)

---

## 6) 삭제 기능 (타겟 Zendesk)

- [x] `services/delete_service.py` (migrated만, 연쇄 삭제, `delete_error`, `retry_failed`)
- [x] `api/routers/delete.py` (`preview`, `execute`, `retry`)

---

## 7) 첨부파일/본문 URL 치환

- [x] 첨부파일 다운로드/업로드 로직
- [x] 본문 URL 치환 (문자열 + HTML 이스케이프 URL 보정)
- [x] 첨부 일부 실패 시 본문 원본 유지 후 마이그레이션 계속

---

## 8) AI OCR — 이미지로 아티클 생성

- [x] `api/routers/ai_ocr.py`
  - [x] `GET/PUT /api/ai-ocr/settings` (OpenAI / Gemini, 활성 제공자)
  - [x] 프롬프트 템플릿 CRUD (`/api/ai-ocr/prompts`)
  - [x] `POST /api/ai-ocr/analyze` (이미지 업로드 → HTML 초안)
  - [x] `POST /api/ai-ocr/create-article` (기본 locale `ko`)
  - [x] `GET /api/ai-ocr/history` (이전 분석 이력)
- [x] `services/ai_ocr_service.py`, `services/article_from_image.py` (Gemini 2.5 Pro 등)
- [x] 프론트: `AiOcrPage`, `AiSettingsPage`, `AiOcrSettingsModal`, `AiOcrHtmlPreview`
- [x] 분석 중 「이전 분석 결과」 비활성화 + 미리보기 `AiOcrCuteSpinner`
- [x] `WorkLogAccordion` API 작업 로그

---

## 9) 이미지 아티클 변환 (소스 아티클 → 타겟)

- [x] `api/routers/image_convert.py`
  - [x] 이미지 포함 아티클 목록/상세/이미지 프록시
  - [x] `POST /api/image-convert/analyze`
  - [x] `POST /api/image-convert/analyze-with-files` (레거시 URL·로컬 파일 OCR)
- [x] `services/image_convert_service.py` (본문 이미지 추출, 호스트 재작성, `external_paste` 진단)
- [x] 프론트: `ConvertImagePage` (소스 아티클 검색·이미지 미리보기·타겟 섹션·OCR·게시)
- [ ] `ConvertImagePage`에도 `AiOcrPage`와 동일한 분석 중 미리보기 스피너·이력 UI (필요 시)

---

## 10) 프론트엔드 — 마이그레이션·공통

- [x] Vite React + `AppSidebar` (인스턴스 / AI 설정 / 이관 / 아티클 생성 메뉴)
- [x] `src/api/client.ts` (수집·마이그레이션·삭제·AI OCR·이미지 변환)
- [x] `src/utils/syncProgressPoll.ts`, `fetchTreeSelection.ts`, `instanceUtils.ts`, `parseApiError.ts`
- [x] 페이지: `InstancesPage`, `MigratePage`, `AiOcrPage`, `ConvertImagePage`, `AiSettingsPage`
- [x] 컴포넌트: `FetchDataTree`, `SelectableSourceTree`, `TargetMigratedTree`, `SyncProgressPanel`, `MigrateProgressPanel`, `CategorySectionPickerModal`, `NestedSectionTreeNodes` 등
- [x] `MigratePage` UX (진행률, 오버레이, 삭제·재시도, 타겟 자동 재수집 체크박스)
- [ ] `PlaceholderPage` — **파일로 아티클 이관** 실제 구현

---

## 11) 품질/운영 준비

- [x] `README.md` (한국어 표준 템플릿, AI·브랜드 수집 반영)
- [ ] 기본 테스트 전략 수립 (서비스/라우터 단위)
  - [x] `tests/test_fetch_cursor_pagination.py` (페이지네이션 유틸만)
- [ ] 배포용 정적 파일 서빙 경로 검증 (`frontend/dist` + FastAPI mount)
- [ ] `render.yaml` 작성
- [ ] `.env.example`에 AI 관련 환경변수 문서화 (현재 키는 DB `ai_ocr_settings` 저장)

---

## 12) 알려진 제한·후속 개선 (메모)

- [ ] `MigratePage` 재진입 시 **진행 중 마이그레이션/수집** 폴링 자동 복구
- [ ] 수집·마이그레이션 진행 상태가 **서버 메모리**에만 있음 → 다중 워커/재시작 시 유실
- [ ] 마이그레이션 직후 타겟 트리는 DB 스냅샷 기준 → **재수집** 전까지 새 항목이 트리에 안 보일 수 있음
- [ ] AI OCR 신규 생성 locale 기본값 `ko` — 타겟 HC가 `ko-kr`만 지원하면 마이그레이션과 동일하게 **타겟 locale 조회 후 정규화** 필요
- [ ] 타 인스턴스 붙여넣기 이미지(`external_paste`)는 Zendesk 재업로드 또는 로컬 파일 OCR로 우회
- [ ] 깊은 섹션 중첩 삭제 시 Zendesk API 순서 실패 가능 → 필요 시 깊이 역순 정렬
- [ ] `uvicorn --reload` 종료 시 연결 대기 메시지 → 두 번째 Ctrl+C 또는 taskkill

---

## 다음 우선순위 (추천)

1. AI OCR `create-article` 시 타겟 Help Center `locales.json` 기반 locale 선택
2. 서비스·라우터 스모크 테스트 (수집 경고·브랜드 단건·마이그레이션 happy path)
3. 진행률 상태 영속화 (Redis 등, 운영 배포 시)
4. `core/config.py` 및 공통 에러 포맷 정리
5. 파일로 아티클 이관 (`migrate-file`) 기능 설계

---

## 작업 로그

- 2026-05-28: 초기 프로젝트 스캐폴딩, DB 모델/Alembic, 서버 실행 및 DB 연결 이슈 해결.
- 2026-05-28~29: 인스턴스·수집·마이그레이션·삭제·첨부/URL 치환·프론트 트리 UI·백그라운드 진행률.
- 2026-05-29: `IMPLEMENTATION_TODO.md` 1차 현행화, 타겟 자동 재수집 체크박스.
- 2026-06-01: 수집 JSON 파싱 실패 경고·`SyncProgressPanel` UX, **브랜드 단건 수집** API/UI.
- 2026-06-01: AI OCR·이미지 아티클 변환·AI 설정·프롬프트 템플릿(Alembic 0007~0013), Gemini 2.5 Pro·로컬 파일 OCR.
- 2026-06-01: `AiOcrPage` 분석 중 스피너·이전 분석 비활성화, `README.md` / `IMPLEMENTATION_TODO.md` 현행화.
