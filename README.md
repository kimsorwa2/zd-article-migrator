# zd-article-migrator

Zendesk Help Center 아티클을 **수집·마이그레이션·삭제**하고, **이미지 기반으로 아티클을 생성·변환**할 수 있는 웹 콘솔입니다.

---

## 🚀 프로젝트 소개

Zendesk Help Center(브랜드 → 카테고리 → 섹션 → 아티클) 구조를 그대로 반영해, 여러 Zendesk 인스턴스 간 콘텐츠 이전과 Vision AI 기반 아티클 작성을 UI로 수행합니다.

**핵심 가치**

- **수집(Fetch)**: Zendesk API로 메타데이터·아티클을 DB에 동기화하고 트리 UI로 확인 (전체 브랜드 / 브랜드 단건)
- **마이그레이션(Migrate)**: 소스에서 선택한 범위를 타겟 Help Center에 생성·업데이트 (중복 정책 지원)
- **삭제(Delete)**: 타겟에 마이그레이션된 항목만 안전하게 삭제 (연쇄 삭제·실패 재시도)
- **이미지 → 아티클(AI OCR)**: 매뉴얼·스크린샷 이미지를 Vision AI로 분석해 Zendesk 아티클 초안 생성
- **이미지 아티클 변환**: 소스 아티클 본문 이미지를 OCR해 타겟 인스턴스에 새 아티클로 게시
- **AI 연동·프롬프트·모니터링**: 다중 AI 연동, **연동별 OCR 프롬프트**, Bedrock 지원, 호출 이력·토큰 메트릭·Excel보내기
- **Zendesk API 요청**: 멀티 제품 API 카탈로그 + Postman 스타일 빌더로 OAuth 프록시 호출·디버깅
- **첨부·URL 치환**: 마이그레이션 시 아티클 본문·첨부 URL을 타겟 인스턴스 기준으로 자동 변환

---

## 🛠 Tech Stack

| 구분 | 기술 |
|------|------|
| 백엔드 | Python 3.11+, FastAPI, SQLAlchemy (async), Alembic, httpx |
| 프론트엔드 | React 18, TypeScript, Vite, lucide-react |
| 데이터베이스 | PostgreSQL (예: Neon) |
| 외부 API | Zendesk Help Center REST API |
| Vision AI | Google Gemini, OpenAI, **AWS Bedrock** (Converse API, Bearer API 키) |

---

## 📦 설치 및 실행

### 사전 요구사항

- Python 3.11+
- Node.js 18+
- PostgreSQL 접속 URL (`DATABASE_URL`)
- Zendesk OAuth: **인스턴스마다** Admin Center에 등록한 Client Identifier·Secret (UI·DB 저장)
  - 앱 공통 기본값(선택): `ZENDESK_OAUTH_REDIRECT_URI`, `ZENDESK_OAUTH_SCOPES` (`backend/.env.example`)
- (선택) Vision AI 키 — **AI 연동** 화면에서 DB에 저장 (환경변수 불필요)
  - Gemini API 키
  - OpenAI API 키
  - Amazon Bedrock API 키 (콘솔 → API keys, Bearer 방식)

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
# (선택) 프로덕션 CORS — 쉼표 구분 Origin 목록
# CORS_ALLOWED_ORIGINS=https://your-frontend.example.com,http://localhost:5173
```

DB 스키마를 반영합니다.

```powershell
python -m alembic upgrade head
python -m alembic current
```

> PowerShell에서 `alembic` 명령이 인식되지 않으면 `python -m alembic upgrade head` 형태를 사용하세요.

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

빌드 결과는 `frontend/dist`에 생성됩니다. 백엔드에서 정적 파일 마운트는 추후 운영 설정에 따릅니다.

### 5) Render 배포 (백엔드)

`backend/render.yaml` 기준으로 API를 배포할 수 있습니다.

- 빌드: `pip install -r requirements.txt && alembic upgrade head`
- 실행: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- 필수 환경변수: `DATABASE_URL`, (권장) `CORS_ALLOWED_ORIGINS`

---

## 💡 주요 기능

### 화면 구성 (사이드바)

사이드바는 **업무 단계** 기준 4개 그룹으로 구성됩니다.

#### 연결 · 설정

| 메뉴 | 설명 |
|------|------|
| **Zendesk 인스턴스** | 인스턴스 CRUD·OAuth 연결·연결 테스트; **Help Center 수집**은 상세 「수집」 탭에서 실행 |
| **AI 연동** | Vision AI 연동(다중)·연결 테스트·**연동별 OCR 프롬프트** 선택 |
| **OCR 프롬프트** | OCR Vision 프롬프트 템플릿 CRUD (시스템·사용자 프롬프트) |

#### Help Center 이관

| 메뉴 | 설명 |
|------|------|
| **인스턴스 간 이관** | 소스/타겟 선택, 트리 기반 마이그레이션·타겟 삭제 |
| **파일로 이관** | (준비 중) CSV·JSON 일괄 등록 |

#### AI 아티클

| 메뉴 | 설명 |
|------|------|
| **이미지 → 아티클 생성** | 이미지 업로드 → AI OCR → 미리보기 → Zendesk 아티클 게시 |
| **이미지 아티클 변환** | 소스 아티클 본문 이미지 선택 → OCR → 타겟에 아티클 생성 |
| **AI 호출 이력** | 입력·출력·추론·총 토큰, 지연 시간, 상세·Excel보내기 |

#### 개발자 도구

| 메뉴 | 설명 |
|------|------|
| **Zendesk API 요청** | Ticketing·Help Center·Voice 등 API 카탈로그 선택, OAuth 프록시로 Zendesk REST API 호출·응답 확인 |

### Zendesk 인스턴스 · 수집

- **리스트**: OAuth·활성 상태 뱃지, 이름·서브도메인 3줄 카드, 이름/서브도메인 필터
- **설정** 탭: 인스턴스 등록·OAuth 재연결, 연결 테스트, 편집, 활성/비활성, 삭제 (2열 설정 표)
- **Help Center 수집** 탭: 브랜드 미리보기·선택 저장, 전체/브랜드 단건 수집, 수집 트리·진행률
- 아티클 **커서 페이지네이션** (`page[size]=100`, `links.next`)
- 백그라운드 수집 + 진행률 폴링, 첨부 조회 일부 실패 시 **경고 목록** 표시 후 수집 계속

### 마이그레이션 · 삭제

- 수집이 완료된 인스턴스(`last_fetched_at`)만 소스/타겟으로 선택
- 소스 트리에서 브랜드·카테고리·섹션·아티클 단위 선택
- 중복 정책: `skip` / `update` / `force`
- 타겟 Help Center 브랜드(서브도메인) 지정, locale은 타겟 `locales.json` 기준으로 정규화 (`ko-kr` → `ko` 등)
- 마이그레이션 진행률 표시, 완료 후 타겟 자동 재수집(선택)
- 타겟 트리: migrated 초록 강조, `delete_error` 주황 강조, 연쇄 삭제·재시도

### AI 연동 · OCR 프롬프트

**AI 연동**: 동일 제공자라도 계정·API 키별로 여러 **연동 프로필**을 등록합니다. 각 연동 행의 **OCR 프롬프트** 셀렉트로 사용할 템플릿을 지정하고, 「사용」으로 OCR·이미지 변환에 쓸 연동을 선택합니다.

**OCR 프롬프트**: 프롬프트 템플릿(시스템·사용자 프롬프트)을 별도 메뉴에서 작성·수정·삭제합니다. OCR 실행 시 **활성 연동에 지정된 프롬프트**가 우선 적용됩니다 (`ai_ocr_connections.prompt_template_id`).

| 제공자 | 대표 모델 | 비고 |
|--------|-----------|------|
| **Gemini** | `gemini-2.5-pro` (권장), `gemini-2.5-flash` | thinking 토큰(Gemini Pro) |
| **OpenAI** | `gpt-4o` (권장), `gpt-4o-mini` | Vision 지원 모델 |
| **AWS Bedrock** | Nova Pro/Lite, Claude 3.5 Sonnet/Haiku | Bearer API 키, 리전 `ap-northeast-2` 기본 |

- 연동별 **연결 테스트** (`POST /api/ai-ocr/connections/{id}/test`)
- API 키는 DB `ai_ocr_connections`에 저장 (`.env`에 AI 키 불필요)

#### AWS Bedrock — inference profile (자동 변환)

Nova·Claude 등은 foundation model ID(`anthropic.claude-3-5-sonnet-20241022-v2:0` 등)를 **on-demand로 직접 호출할 수 없습니다.** 백엔드 `resolve_bedrock_model`이 연동 **AWS 리전**에 맞게 inference profile ID를 붙입니다.

| AWS 리전 | 접두사 | Claude 3.5 Sonnet v2 호출 예 |
|----------|--------|------------------------------|
| `ap-northeast-2` 등 APAC | `apac.` | `apac.anthropic.claude-3-5-sonnet-20241022-v2:0` |
| `us-east-1` 등 US | `us.` | `us.anthropic.claude-3-5-sonnet-20241022-v2:0` |
| `eu-central-1` 등 EU | `eu.` | `eu.anthropic.claude-3-5-sonnet-20241022-v2:0` |

AI 연동 UI에서는 foundation model ID를 선택하면 되고, **연결 테스트·OCR 시 자동 변환**됩니다. AI 연동 추가 모달에서 리전별 실제 호출 ID를 미리 볼 수 있습니다.

추가 확인 사항:

1. [Bedrock 콘솔](https://console.aws.amazon.com/bedrock/) → **Model access**에서 사용 모델 **Enabled**
2. 연동 **AWS 리전**과 콘솔 리전 일치 (`ap-northeast-2` 기본)
3. Bedrock **API keys**에서 발급한 키 입력 (Bearer, IAM Access Key 불필요)

### AI OCR · 이미지 아티클 변환

- **이미지 → 아티클 생성**: 업로드 이미지 분석, 이전 분석 이력 불러오기, HTML 본문 미리보기, 아티클 생성 (기본 locale `ko`)
- **이미지 아티클 변환**: 소스 인스턴스에서 이미지 포함 아티클 검색, 본문 이미지 미리보기, API/로컬 파일 OCR, 타겟 섹션에 게시
- 레거시·타 인스턴스 붙여넣기 이미지 URL은 Zendesk API로 받을 수 없을 때 **로컬 파일 업로드**로 OCR 가능
- 분석 중 미리보기 로딩 스피너, API 작업 로그(`WorkLogAccordion`) 표시

### AI 호출 이력 (모니터링)

- Gemini·OpenAI·Bedrock 공통 형식: **입력·출력·추론·총 토큰**, 지연 시간, 종료 이유
- Gemini는 `thoughtsTokenCount`가 추론 토큰, Bedrock·OpenAI 일반 호출은 추론 `0` (미사용)
- 호출별 상세(프롬프트 스냅샷·AI 원문·파싱 오류) 모달
- 이력 **Excel보내기** (전체 / 선택 행)

### Zendesk API 요청 (개발자 도구)

Postman 스타일 요청 빌더로 등록된 Zendesk 인스턴스에 REST API를 호출합니다. access token은 **백엔드 프록시**에서만 사용합니다.

**카탈로그**

| 제품 | 설명 |
|------|------|
| **Ticketing** | Tickets, Users, Organizations 등 Support API |
| **Help Center** | Articles, Categories, Sections 등 |
| **Voice (TPE)** | Talk Partner Edition API |
| **Custom Data** | Custom Objects API |
| **Omnichannel** | Messaging·Sunshine Conversations 등 |

- **빠르게 찾기** + 대분류·중분류·API 선택·검색
- API 문서 링크(제품 소개·개별 operation) 바로가기

**요청 빌더**

- Method + Path URL 바, Path ↔ Params 양방향 동기화
- **Params / Query / Headers / Body** 탭 (KV 테이블: Key·Value·Description·활성 체크박스)
- Body 서브탭: JSON · Raw · Files(준비 중)
- 응답 JSON·HTTP 상태·지연 시간·cURL 복사

**엔드포인트**: `GET /api/zendesk-proxy/catalog`, `POST /api/zendesk-proxy/request`

### API 개요

| 영역 | 대표 엔드포인트 |
|------|-----------------|
| 인스턴스 | `GET/POST/PATCH/DELETE /api/instances`, `POST .../connection-test` |
| 수집 | `POST /api/fetch/{id}/sync`, `POST /api/fetch/{id}/brands/{brand_id}/sync`, `GET .../sync/progress`, `GET .../detail` |
| 마이그레이션 | `POST /api/migrate/execute`, `GET /api/migrate/progress`, `GET /api/migrate/tree`, `GET /api/migrate/overlay` |
| 삭제 | `POST /api/delete/preview`, `POST /api/delete/execute`, `POST /api/delete/retry` |
| AI OCR | `GET /api/ai-ocr/model-options`, `GET/PUT /api/ai-ocr/settings` |
| AI 연동 | `POST/PUT/DELETE /api/ai-ocr/connections`, `POST .../test`, `PUT .../activate` |
| AI 프롬프트 | `GET/POST/PUT/DELETE /api/ai-ocr/prompts` |
| AI 분석 | `POST /api/ai-ocr/analyze`, `POST /api/ai-ocr/create-article` |
| AI 이력 | `GET /api/ai-ocr/history`, `GET /api/ai-ocr/history/metrics` |
| 이미지 변환 | `GET /api/image-convert/articles`, `POST /api/image-convert/analyze`, `POST .../analyze-with-files` |
| Zendesk API 프록시 | `GET /api/zendesk-proxy/catalog`, `POST /api/zendesk-proxy/request` |

자세한 구현·진행 상황·알려진 제한은 [IMPLEMENTATION_TODO.md](./IMPLEMENTATION_TODO.md)를 참고하세요.

---

## 🤝 협업 규칙

### 커밋 메시지

[Conventional Commits](https://www.conventionalcommits.org/) 형식을 사용하고, **메시지는 한국어**로 작성합니다.

```
feat: AI 연동 다중 프로필 및 Bedrock Converse API 추가
fix: Bedrock 단기 API 키 길이 제한 확장 (Alembic 0019)
docs: README Bedrock inference profile 안내 보완
```

### 코드 스타일

- **주석**: 비즈니스 로직·복잡한 분기는 한글 주석으로 의도를 명확히 남깁니다.
- **TypeScript**: `any` 지양, 인터페이스/타입으로 API 응답을 정의합니다.
- **Python**: Early return, 매직 넘버는 상수로 분리합니다.
- **범위**: 요청과 무관한 리팩터링·포맷 변경은 PR에 포함하지 않습니다.

### 브랜치·PR

- 기능 단위로 브랜치를 나누고, PR 설명에 **변경 요약**과 **로컬 테스트 방법**을 적습니다.
- `.env`, OAuth client secret, DB 비밀번호, Bedrock API 키는 **커밋하지 않습니다**.

---

## 프로젝트 구조

```
zd-article-migrator/
├── backend/
│   ├── api/routers/          # instances, fetch, migrate, delete, ai_ocr, image_convert, zendesk_proxy
│   ├── constants/            # Zendesk API 카탈로그 (Ticketing, HC, Voice, Custom Data, Omnichannel)
│   ├── db/                   # SQLAlchemy 모델·비동기 세션·connection
│   ├── services/
│   │   ├── bedrock_runtime.py    # Bedrock Converse (Bearer httpx)
│   │   ├── ai_ocr_service.py     # 연동·설정·이력·분석 오케스트레이션
│   │   ├── ai_usage_metrics.py   # 제공자별 토큰 usage 정규화
│   │   ├── article_from_image.py # Gemini / OpenAI / Bedrock Vision
│   │   └── ...                   # Zendesk·수집·마이그레이션·삭제·이미지 변환
│   ├── alembic/versions/     # 0001 ~ 0020 (연동·이력·연동별 프롬프트 등)
│   ├── tests/
│   ├── render.yaml           # Render 백엔드 배포 예시
│   └── main.py
├── frontend/
│   └── src/
│       ├── pages/            # Instances, Migrate, AiOcr, ConvertImage, AiSettings, AiPromptManage, AiOcrMonitor, ApiRequest
│       ├── components/       # 트리·진행률·ApiRequestParamsPanel·ZendeskApiCatalogPicker
│       ├── constants/        # aiModelOptions.ts (제공자별 모델 목록)
│       └── api/client.ts
├── IMPLEMENTATION_TODO.md
└── README.md
```

---

## 알려진 제한·후속 작업 (요약)

- Bedrock 리전을 US/EU로 바꾸면 inference profile 접두사도 `us.`/`eu.`로 바뀜 (연동 리전과 콘솔 Model access 일치 필요)
- 수집·마이그레이션 진행 상태는 **서버 메모리** — 다중 워커·재시작 시 유실 가능
- AI OCR 신규 아티클 locale 기본값 `ko` — 타겟 HC가 `ko-kr`만 지원하면 타겟 locale 정규화 연동 검토
- **파일로 이관** 메뉴는 Placeholder 상태

전체 목록은 [IMPLEMENTATION_TODO.md](./IMPLEMENTATION_TODO.md) §12를 참고하세요.

---

## 라이선스

별도 명시가 없는 한, 저장소 소유자의 정책을 따릅니다.

## 문의

- GitHub: [kimsorwa2](https://github.com/kimsorwa2)
- 이메일: kimsorwa@gmail.com
