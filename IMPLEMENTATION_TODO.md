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

- `upgrade head`: 최신 마이그레이션까지 DB 스키마 반영
- `current`: 현재 DB에 반영된 리비전 확인
- 참고: PowerShell에서 `alembic` 명령이 안 잡히면 `python -m alembic ...` 형태를 사용

### 2) 백엔드 서버 실행

```powershell
cd C:\Users\kimso\Documents\workspace\demo\zd-article-migrator\backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- 기본 접속 주소: `http://localhost:8000`
- 헬스체크 예시: `http://localhost:8000/health`

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
  - [x] `instances`
  - [x] `brands`
  - [x] `categories`
  - [x] `sections`
  - [x] `articles`
  - [x] `migration_mappings`
- [x] `backend/db/database.py` 비동기 DB 연결 설정
- [x] Alembic 초기 구성 (`backend/alembic`, `alembic.ini`, 초기 revision 파일)
- [x] `backend/main.py` FastAPI 기본 설정 + 라우터 등록
- [x] `backend/.env.example` 작성
- [x] Neon 연결 및 `alembic current` 정상 확인
- [ ] `alembic upgrade head` 실행 결과 재확인 (`0001_initial_schema` 반영 확인)

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
  - [x] 공통 GET/POST/PATCH/DELETE 메서드
  - [x] 요청 간 지연(0.5초) 적용
  - [x] 429 응답 시 `Retry-After` 기반 재시도(최대 3회)
  - [x] 공통 예외 처리 및 메시지 표준화

---

## 3) 인스턴스 관리 API

- [x] `api/schemas.py`에 인스턴스/브랜드 관련 스키마 추가
- [x] `api/routers/instances.py` CRUD 구현
  - [x] 통합 인스턴스 생성 (`POST /api/instances`)
  - [x] 인스턴스 목록/상세 조회
  - [x] 인스턴스 수정·활성/비활성 전환
  - [x] 인스턴스 삭제 (`DELETE /api/instances/{id}`, CASCADE, 수집 중 409)
- [x] 등록 시 브랜드 미리보기·선택 저장
- [x] 연결 테스트 API (`GET /api/v2/account`)

---

## 4) 데이터 수집 (Zendesk → DB)

- [x] `services/fetch_service.py` 구현
  - [x] 브랜드별 카테고리/섹션/아티클 수집·업서트
  - [x] 아티클 **커서 페이지네이션** (`page[size]=100`, `links.next` / `meta.has_more`)
  - [x] 수집 완료 시 `instances.last_fetched_at` 갱신
- [x] 백그라운드 수집 + 진행률
  - [x] `services/fetch_progress.py` (`FetchProgressTracker`)
  - [x] `services/fetch_sync_job.py`
  - [x] `POST /api/fetch/{instance_id}/sync` → **202** (백그라운드 시작)
  - [x] `GET /api/fetch/{instance_id}/sync/progress` (폴링)
- [x] `GET /api/fetch/{instance_id}/detail` (트리 UI용 상세)
- [x] 프론트: `InstancesPage` 수집 진행률(`SyncProgressPanel`), 실패 메시지(`NoticeBanner`)

---

## 5) 마이그레이션 실행 (소스 → 타겟)

- [x] `services/migration_service.py`
  - [x] 브랜드 → 타겟 **카테고리** (이름 기준 매핑/생성)
  - [x] 소스 카테고리 → 타겟 **상위 섹션**
  - [x] 소스 섹션 → 타겟 **하위 섹션** (`parent_section_id`)
  - [x] 아티클 생성/업데이트 + 첨부·본문 URL 치환
  - [x] 중복 정책 `skip` / `update` / `force`
  - [x] 타겟 Help Center **브랜드 서브도메인** (`target_brand_id`, `_resolve_target_help_center`)
- [x] `migration_mappings` 생성·갱신
- [x] 백그라운드 마이그레이션 + 진행률
  - [x] `services/migrate_progress.py`
  - [x] `services/migrate_sync_job.py`
  - [x] `POST /api/migrate/execute` → **202**
  - [x] `GET /api/migrate/progress?source_instance_id=&target_instance_id=`
- [x] `GET /api/migrate/tree` (소스 선택 트리 + 매핑 상태, `get_selection_tree` 버그 수정)
- [x] `GET /api/migrate/overlay` (타겟 트리 하이라이트·삭제용 migrated / `delete_error` 오버레이)

---

## 6) 삭제 기능 (타겟 Zendesk)

- [x] `services/delete_service.py`
  - [x] **migrated** 매핑만 삭제 (미마이그레이션 항목 무시)
  - [x] 타겟 트리 선택 → 소스 A ID로 확장·**하위 연쇄 삭제** (`resolve_source_selection`)
  - [x] 타겟 API 호출 시 마이그레이션과 동일 `target_brand_id` 서브도메인
  - [x] 삭제 순서: 아티클 → 섹션 → 카테고리(브랜드 매핑)
  - [x] 실패 시 `delete_error` + `error_message` 보존
  - [x] 성공 시 매핑 레코드 삭제
  - [x] 응답 `failed_items` 목록
  - [x] `retry_failed` (`delete_error` 재시도)
- [x] `api/routers/delete.py`
  - [x] `POST /api/delete/preview`
  - [x] `POST /api/delete/execute`
  - [x] `POST /api/delete/retry`

---

## 7) 첨부파일/본문 URL 치환

- [x] 첨부파일 다운로드/업로드 로직
- [x] 본문 URL 치환 (문자열 + HTML 이스케이프 URL 보정)
- [x] 첨부 일부 실패 시 본문 원본 유지 후 마이그레이션 계속

---

## 8) 프론트엔드 구현

- [x] Vite React (`src/main.tsx`, `src/App.tsx`) — 탭: **인스턴스 관리** / **마이그레이션**
- [x] `src/api/client.ts` (수집·마이그레이션 진행률, 오버레이, 삭제 재시도 포함)
- [x] `src/utils/syncProgressPoll.ts` (수집 완료 폴링 공용)
- [x] `src/utils/fetchTreeSelection.ts`, `instanceUtils.ts`, `parseApiError.ts`
- [x] 페이지
  - [x] `InstancesPage` (인스턴스 CRUD + Help Center 수집 + `FetchDataTree`)
  - [x] `MigratePage` (소스/타겟 분할, 마이그레이션·삭제 UX)
- [x] 주요 컴포넌트
  - [x] `InstanceForm`, `FetchDataTree`, `SelectableSourceTree`, `TargetMigratedTree`
  - [x] `SyncProgressPanel`, `MigrateProgressPanel`, `LoadingPanel`, `NoticeBanner`
  - [x] `StatusBadge` (레거시 `ArticleTree`는 유지, 신규 화면은 위 트리 컴포넌트 사용)
- [x] `MigratePage` UX
  - [x] 수집 완료 인스턴스만 소스/타겟 선택 가능 (`last_fetched_at`)
  - [x] 타겟 브랜드 다중 시 셀렉트 + **마이그레이션 실행** 버튼(타겟 패널)
  - [x] 마이그레이션 진행률 바
  - [x] (선택) 마이그레이션 완료 후 **타겟 자동 재수집** 체크박스
  - [x] 타겟 트리: migrated 초록 강조, `delete_error` 주황 강조
  - [x] 카테고리·섹션 체크박스 + 카드 내 **선택 항목 삭제** / **삭제 실패 재시도**

---

## 9) 품질/운영 준비

- [ ] 기본 테스트 전략 수립 (서비스/라우터 단위)
- [ ] 배포용 정적 파일 서빙 경로 검증 (`frontend/dist`)
- [ ] `render.yaml` 작성
- [ ] `README.md` 작성 (한국어 표준 템플릿 반영)

---

## 10) 알려진 제한·후속 개선 (메모)

- [ ] `MigratePage` 재진입 시 **진행 중 마이그레이션/수집** 폴링 자동 복구 (인스턴스 페이지는 수집 중 마운트 시만 폴링)
- [ ] 수집·마이그레이션 진행 상태가 **서버 메모리**에만 있음 → 다중 워커/재시작 시 유실
- [ ] 마이그레이션 직후 타겟 트리는 DB 스냅샷 기준 → **재수집** 전까지 새 항목이 트리에 안 보일 수 있음 (오버레이·매핑은 동작)
- [ ] 깊은 섹션 중첩 삭제 시 Zendesk API 순서 실패 가능 → 필요 시 깊이 역순 정렬
- [ ] `uvicorn --reload` 종료 시 연결 대기 메시지 → 두 번째 Ctrl+C 또는 taskkill

---

## 다음 우선순위 (추천)

1. `README.md` + 로컬/배포 실행 가이드 정리
2. 서비스·라우터 스모크 테스트 (마이그레이션/삭제/수집 happy path)
3. 진행률 상태 영속화 또는 Redis 등 (운영 배포 시)
4. `core/config.py` 및 공통 에러 포맷 정리

---

## 작업 로그

- 2026-05-28: 초기 프로젝트 스캐폴딩, DB 모델/Alembic, 서버 실행 및 DB 연결 이슈 해결.
- 2026-05-28: 인스턴스 API, Zendesk 클라이언트(지연/재시도), 데이터 수집 API 1차.
- 2026-05-28: 마이그레이션 API 1차(브랜드/카테고리/섹션/아티클 + 매핑).
- 2026-05-28: 삭제 API 1차(미리보기/실행, `delete_error`, 매핑 정리).
- 2026-05-28: 첨부 재업로드·본문 URL 치환, 프론트 1차 화면(인스턴스/수집/마이그레이션 탭).
- 2026-05-28: 마이그레이션 트리 선택 UI, `/api/migrate/tree`, UI 리디자인·사이드바 레이아웃, lucide 아이콘.
- 2026-05-28: 인스턴스 이름 자동 생성, Zendesk ID `BIGINT` 확장.
- 2026-05-29: 수집 커서 페이지네이션·백그라운드 sync·진행률 API·인스턴스 삭제(CASCADE).
- 2026-05-29: `InstancesPage` 통합(수집+트리), App 메뉴 정리(인스턴스/마이그레이션 2탭).
- 2026-05-29: `MigratePage` 소스·타겟 분할, 타겟 `target_brand_id`, 타겟 Help Center 트리.
- 2026-05-29: 마이그레이션 백그라운드 실행·`GET /migrate/progress`, `MigrateProgressPanel`.
- 2026-05-29: `GET /migrate/overlay`, `TargetMigratedTree`(migrated 강조·체크박스·삭제).
- 2026-05-29: 타겟 기준 삭제·연쇄 삭제·`target_brand_id` subdomain, 삭제 버튼 타겟 트리 카드 내부로 이동.
- 2026-05-29: `POST /delete/retry`, `failed_items`, 삭제 실패 UI(주황·개별/일괄 재시도).
- 2026-05-29: 마이그레이션 완료 후 타겟 자동 재수집(선택 체크박스), `IMPLEMENTATION_TODO.md` 현행화.
