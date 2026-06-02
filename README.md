# zd-article-migrator

Zendesk Help Center 아티클을 **수집·마이그레이션·삭제**하고, **이미지 기반으로 아티클을 생성·변환**할 수 있는 웹 콘솔입니다.

---

## 🚀 프로젝트 소개

Zendesk Help Center(브랜드 → 카테고리 → 섹션 → 아티클) 구조를 그대로 반영해, 여러 Zendesk 인스턴스 간 콘텐츠 이전과 AI 기반 아티클 작성을 UI로 수행합니다.

**핵심 가치**

- **수집(Fetch)**: Zendesk API로 메타데이터·아티클을 DB에 동기화하고 트리 UI로 확인 (전체 브랜드 / 브랜드 단건)
- **마이그레이션(Migrate)**: 소스에서 선택한 범위를 타겟 Help Center에 생성·업데이트 (중복 정책 지원)
- **삭제(Delete)**: 타겟에 마이그레이션된 항목만 안전하게 삭제 (연쇄 삭제·실패 재시도)
- **이미지 → 아티클(AI OCR)**: 매뉴얼 이미지를 Vision AI로 분석해 Zendesk 아티클 초안 생성
- **이미지 아티클 변환**: 소스 아티클 본문 이미지를 OCR해 타겟 인스턴스에 새 아티클로 게시
- **첨부·URL 치환**: 마이그레이션 시 아티클 본문·첨부 URL을 타겟 인스턴스 기준으로 자동 변환

---

## 🛠 Tech Stack

| 구분 | 기술 |
|------|------|
| 백엔드 | Python 3.11+, FastAPI, SQLAlchemy (async), Alembic, httpx |
| 프론트엔드 | React 18, TypeScript, Vite, lucide-react |
| 데이터베이스 | PostgreSQL (예: Neon) |
| 외부 API | Zendesk Help Center REST API, OpenAI / Google Gemini (Vision) |

---

## 📦 설치 및 실행

### 사전 요구사항

- Python 3.11+
- Node.js 18+
- PostgreSQL 접속 URL
- Zendesk API 토큰 (이메일 + API 토큰, Basic Auth)
- (선택) OpenAI / Gemini API 키 — AI OCR·이미지 변환 기능 사용 시

### 1) 저장소 클론

```powershell
git clone https://github.com/kimsorwa2/zd-article-migrator.git
cd zd-article-migrator
```

### 2) 백엔드 설정

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

`.env` 파일을 생성합니다 (`backend/.env.example` 참고).

```env
DATABASE_URL=postgresql+asyncpg://user:password@host/dbname
ENVIRONMENT=development
```

DB 스키마를 반영합니다.

```powershell
python -m alembic upgrade head
python -m alembic current
```

서버를 실행합니다.

```powershell
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- API: http://localhost:8000
- 헬스체크: http://localhost:8000/api/health

### 3) 프론트엔드 설정

새 터미널에서:

```powershell
cd frontend
npm install
npm run dev
```

- UI: http://localhost:5173
- `/api` 요청은 Vite 프록시를 통해 `http://localhost:8000`으로 전달됩니다.

### 4) 프로덕션 빌드 (선택)

```powershell
cd frontend
npm run build
```

빌드 결과는 `frontend/dist`에 생성됩니다.

---

## 💡 주요 기능

### 화면 구성 (사이드바)

| 메뉴 | 설명 |
|------|------|
| **인스턴스 관리** | Zendesk 인스턴스 CRUD, Help Center 수집, 수집 트리 조회 |
| **AI 설정** | Vision AI 제공자(OpenAI/Gemini), API 키, OCR 프롬프트 템플릿 관리 |
| **인스턴스 간 이관** | 소스/타겟 선택, 트리 기반 마이그레이션·타겟 삭제 |
| **이미지로 아티클 생성** | 이미지 업로드 → AI OCR → 미리보기 → Zendesk 아티클 게시 |
| **이미지 아티클 변환** | 소스 아티클 본문 이미지 선택 → OCR → 타겟에 아티클 생성 |
| **파일로 아티클 이관** | (준비 중) CSV·JSON 일괄 등록 |

### 인스턴스 관리 · 수집

- Zendesk 인스턴스(서브도메인, 이메일, API 토큰) 등록·수정·삭제
- 연결 테스트 및 브랜드(Help Center) 미리보기·선택 저장
- **전체 브랜드 수집**: 선택된 모든 브랜드를 순차 동기화
- **브랜드 단건 수집**: 트리에서 「이 브랜드 수집」으로 필요한 브랜드만 갱신
- 백그라운드 수집 + 진행률 폴링, 첨부 조회 일부 실패 시 **경고 목록** 표시 후 수집 계속

### 마이그레이션 · 삭제

- 수집이 완료된 인스턴스(`last_fetched_at`)만 소스/타겟으로 선택
- 소스 트리에서 브랜드·카테고리·섹션·아티클 단위 선택
- 중복 정책: `skip` / `update` / `force`
- 타겟 Help Center 브랜드(서브도메인) 지정, locale은 타겟 `locales.json` 기준으로 정규화 (`ko-kr` → `ko` 등)
- 마이그레이션 진행률 표시, 완료 후 타겟 자동 재수집(선택)
- 타겟 트리: migrated 초록 강조, `delete_error` 주황 강조, 연쇄 삭제·재시도

### AI OCR · 이미지 아티클 변환

- **이미지로 아티클 생성**: 업로드 이미지 분석, 이전 분석 이력 불러오기, HTML 본문 미리보기, 아티클 생성 (기본 locale `ko`)
- **이미지 아티클 변환**: 소스 인스턴스에서 이미지 포함 아티클 검색, 본문 이미지 미리보기, API/로컬 파일 OCR, 타겟 섹션에 게시
- 레거시·타 인스턴스 붙여넣기 이미지 URL은 Zendesk API로 받을 수 없을 때 **로컬 파일 업로드**로 OCR 가능
- 분석 중 미리보기 영역 로딩 스피너, API 작업 로그 표시

### API 개요

| 영역 | 대표 엔드포인트 |
|------|-----------------|
| 인스턴스 | `GET/POST/PATCH/DELETE /api/instances`, `POST .../connection-test` |
| 수집 | `POST /api/fetch/{id}/sync`, `POST /api/fetch/{id}/brands/{brand_id}/sync`, `GET .../sync/progress`, `GET .../detail` |
| 마이그레이션 | `POST /api/migrate/execute`, `GET /api/migrate/progress`, `GET /api/migrate/tree`, `GET /api/migrate/overlay` |
| 삭제 | `POST /api/delete/preview`, `POST /api/delete/execute`, `POST /api/delete/retry` |
| AI OCR | `GET/PUT /api/ai-ocr/settings`, `POST /api/ai-ocr/analyze`, `POST /api/ai-ocr/create-article`, `GET /api/ai-ocr/history` |
| 이미지 변환 | `GET /api/image-convert/articles`, `POST /api/image-convert/analyze`, `POST /api/image-convert/analyze-with-files` |

자세한 구현·진행 상황은 [IMPLEMENTATION_TODO.md](./IMPLEMENTATION_TODO.md)를 참고하세요.

---

## 🤝 협업 규칙

### 커밋 메시지

[Conventional Commits](https://www.conventionalcommits.org/) 형식을 사용하고, **메시지는 한국어**로 작성합니다.

```
feat: 브랜드 단건 Help Center 수집 API 추가
fix: 수집 중 JSON 파싱 실패 시 경고만 기록하고 계속 진행
docs: README AI OCR 섹션 보완
```

### 코드 스타일

- **주석**: 비즈니스 로직·복잡한 분기는 한글 주석으로 의도를 명확히 남깁니다.
- **TypeScript**: `any` 지양, 인터페이스/타입으로 API 응답을 정의합니다.
- **Python**: Early return, 매직 넘버는 상수로 분리합니다.
- **범위**: 요청과 무관한 리팩터링·포맷 변경은 PR에 포함하지 않습니다.

### 브랜치·PR

- 기능 단위로 브랜치를 나누고, PR 설명에 **변경 요약**과 **로컬 테스트 방법**을 적습니다.
- `.env`, API 토큰, DB 비밀번호는 **커밋하지 않습니다**.

---

## 프로젝트 구조

```
zd-article-migrator/
├── backend/
│   ├── api/routers/       # instances, fetch, migrate, delete, ai_ocr, image_convert
│   ├── db/                # SQLAlchemy 모델·세션
│   ├── services/          # Zendesk·수집·마이그레이션·삭제·AI OCR·이미지 변환
│   ├── alembic/versions/  # 0001 ~ 0013 (AI OCR·프롬프트 템플릿 등)
│   ├── tests/
│   └── main.py
├── frontend/
│   └── src/
│       ├── pages/         # InstancesPage, MigratePage, AiOcrPage, ConvertImagePage, AiSettingsPage
│       ├── components/    # 트리·진행률·OCR 미리보기·설정 모달
│       └── api/client.ts
├── IMPLEMENTATION_TODO.md
└── README.md
```

---

## 라이선스

별도 명시가 없는 한, 저장소 소유자의 정책을 따릅니다.

## 문의

- GitHub: [kimsorwa2](https://github.com/kimsorwa2)
- 이메일: kimsorwa@gmail.com
