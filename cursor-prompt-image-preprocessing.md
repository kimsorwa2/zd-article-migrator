# Cursor 작업 프롬프트: AI-OCR 이미지 전처리 파이프라인

> **상태: 구현 완료** (2026-06-02) — Gemini·OpenAI·Bedrock 공통 파이프라인  
> **이 문서 = 실제 코드베이스에 반영된 내용** (초안 프롬프트를 프로젝트에 맞게 수정·구현한 결과)

## 목표

Nova Pro 등 한국어 밀도 높은 이미지에서 시각 인식이 약한 모델을 위해,
AI API 호출 **전**에 이미지를 전처리하여 텍스트 인식률을 높인다.

---

## 배경 및 문제

기존 `article_from_image.py`는 업로드 바이트를 그대로 Vision API에 전송했다.

Nova Pro 테스트에서:
- 밀도 높은 한국어 표에서 같은 텍스트 반복 환각
- 튀김기 조리 그룹 누락
- 원인: 해상도·대비 부족으로 인한 시각 인식 실패

---

## 구현 요약 (현재 코드 기준)

### 1. `backend/services/image_preprocess.py` (신규)

| 항목 | 내용 |
|------|------|
| 메인 API | `apply_ocr_image_preprocessing()` → `OcrPreprocessResult` dataclass |
| 보조 API | `preprocess_for_ocr()`, `preprocess_metrics()` (프롬프트 호환·단순 호출용) |
| 파이프라인 | EXIF 보정(`ImageOps.exif_transpose`) → RGB(투명 배경 흰색) → 장변 업/다운스케일 → 대비 1.5× → 선명도 1.3× → PNG |
| 용량 가드 | 15MB 초과 시 업스케일 없이 재시도 → 여전히 초과 또는 PIL 오류 시 **원본 fallback** |
| 스킵 사유 | `skipped_reason`: `disabled` \| `size_limit` \| `error` |
| A/B 태그 | `experiment_tag_for_preprocess()` → `preprocess_on` / `preprocess_off` |

상수: 장변 &lt; 2000px → 1.5× 업스케일, 장변 &gt; 4000px → 4000px 다운스케일.

### 2. `backend/services/article_from_image.py`

- `image_bytes_to_article(..., preprocess: bool = True)` — **모든 provider 공통** 진입점에서 전처리
- `_attach_preprocess_metrics()`로 Gemini/OpenAI/Bedrock 응답 `_metrics`에 병합:
  - `preprocessed`, `original_size_kb`, `processed_size_kb`, (선택) `preprocess_skipped_reason`
- `api_secret`, `aws_region` 등 Bedrock 인자는 기존 시그니처 유지 (전처리와 무관)

### 3. DB — Alembic `0021_ai_ocr_preprocess_flag`

- `ai_ocr_analysis_history.preprocessed` (Boolean)
- `ai_ocr_analysis_history.processed_image_size_kb` (Integer)
- **revision `0021`** (`0020_ai_ocr_connection_prompt` 다음) — 초안의 `0017`은 이미 다른 마이그레이션에서 사용 중

### 4. API

| 엔드포인트 | 파라미터 | 라우터 함수명 |
|-----------|---------|----------------|
| `POST /ai-ocr/analyze` | `?preprocess=true` (기본 ON) | `analyze_manual_image` |
| `POST /image-convert/analyze` | `?preprocess=true` | `analyze_image_convert_article` |
| `POST /image-convert/analyze-with-files` | `?preprocess=true` | `analyze_image_convert_article_with_files` |

### 5. 서비스·이력

- `AiOcrService.analyze_image(..., preprocess=True)` → `image_bytes_to_article` → `_save_analysis_history`에 전처리 필드·`experiment_tag` 저장
- `ImageConvertService.analyze_article(..., preprocess=True)` → 동일 전처리, **OCR 이력 DB에는 미저장**

### 6. 프론트엔드

- `AiOcrPage.tsx`, `ConvertImagePage.tsx` — 전처리 체크박스 (기본 ON), `.form-checkbox-label` (전역 `label`/`input` CSS 충돌 회피)
- `AiOcrMonitorPage.tsx` — 전처리 여부·전처리 후 KB 컬럼
- `exportAiOcrHistoryExcel.ts` — Excel 컬럼 추가
- `client.ts` — `analyzeAiOcrImage(file, preprocess?)`, image-convert analyze에 `preprocess` query

### 7. 의존성

- `backend/requirements.txt`: **`Pillow==12.2.0`** (로컬 Python 3.14에서 11.x wheel 빌드 실패 → 12.2.0으로 고정)

---

## 검증 체크리스트

1. 동일 이미지로 전처리 ON/OFF 비교 (Nova·Claude·Gemini·Bedrock)
2. AI 호출 모니터링: `preprocessed`, `processed_image_size_kb`, `experiment_tag`
3. 대용량 PNG: 15MB 근처에서 fallback·로그(`size_limit`) 확인
4. 배포: `alembic upgrade head` (0021)

---

## 참고 파일

| 영역 | 파일 |
|------|------|
| 전처리 | `backend/services/image_preprocess.py` |
| Vision 호출 | `backend/services/article_from_image.py` |
| OCR 서비스·이력 | `backend/services/ai_ocr_service.py` |
| 이미지 변환 | `backend/services/image_convert_service.py`, `api/routers/image_convert.py` |
| API | `api/routers/ai_ocr.py`, `api/schemas.py` |
| DB | `db/models.py`, `alembic/versions/0021_ai_ocr_preprocess_flag.py` |

---

## 초안 프롬프트 vs 실제 구현 (클로드 전달용)

**질문:** 처음 준 `cursor-prompt-image-preprocessing.md` 그대로인가?  
**답:** **아니요.** 초안은 Nova 중심·프로젝트 미검증 상태였고, 구현 전에 **레포 현황(Alembic head, Bedrock 연동, 15MB 제한, image-convert 경로 등)에 맞게 수정한 뒤** 아래 표와 같이 구현했다. **현재 이 문서가 “적용된 내용”의 기준**이다.

### 차이 요약표

| 구분 | 초안 프롬프트 | 실제 구현 | 달라진 이유 |
|------|---------------|-----------|-------------|
| 메인 전처리 함수 | `preprocess_for_ocr()` 만 호출 | **`apply_ocr_image_preprocessing()`** + `OcrPreprocessResult` | media_type 변경·스킵 사유·enabled 플래그를 한 번에 반환해 Vision 호출부·이력 저장이 단순해짐. `preprocess_for_ocr`는 하위 호환용으로 유지 |
| PNG 변환 | `_convert_to_png()` → `(bytes, "image/png")` | **`_encode_png()`** + result의 `media_type` | 동일 목적, dataclass 한곳에서 bytes·MIME 관리 |
| metrics | `preprocess_metrics()`를 `article_from_image`에서 별도 호출 | **`apply_ocr` 결과 + `_attach_preprocess_metrics()`** | 중복 계산 제거, 실패 fallback 시에도 일관된 메트릭 |
| 파이프라인 단계 | 크기→대비→선명도→PNG (4단계) | **EXIF 회전 + RGB(알파→흰 배경) 추가** | 휴대폰·스캔 이미지 회전·투명 PNG가 OCR에 자주 깨짐 |
| 15MB 초과 | (초안에 없음) | **업스케일 생략 재시도 → 원본 fallback** | `MAX_IMAGE_BYTES`(15MB)와 동일 상한; PNG 업스케일 후 업로드 거부 방지 |
| PIL 예외 | (초안에 없음) | **catch 후 원본 사용 (`skipped_reason=error`)** | 전처리 실패가 전체 OCR 실패로 이어지지 않게 |
| Alembic | `0017_ai_ocr_preprocess_flag` | **`0021_ai_ocr_preprocess_flag`** | `0017`~`0020`은 이미 compare/metrics/connection_prompt 등에 사용 |
| Pillow | “이미 설치되어 있을 가능성” | **`requirements.txt`에 `Pillow==12.2.0` 명시** | 레포에 없었고, 11.2.1은 Python 3.14에서 빌드 실패 |
| `image_bytes_to_article` | `preprocess`만 추가, Bedrock 인자 누락 | **`preprocess` 추가 + 기존 `api_secret`/`aws_region` 유지** | 초안 작성 시점보다 Bedrock 연동이 이미 확장된 상태 |
| API 라우터 이름 | `analyze_image` | **`analyze_manual_image`** | 실제 `ai_ocr.py` 함수명과 일치 (문서만 틀렸음) |
| 적용 범위 | AI-OCR analyze 위주 | **+ `ImageConvertService` / image-convert 라우터** | `image_bytes_to_article`를 쓰는 모든 경로에 동일 품질 적용 |
| DB·모니터 | 컬럼 2개 제안 | **동일 + `list_analysis_history`·Monitor·Excel 연동** | 초안 “검증” 섹션에 있던 모니터 요구를 구현에 포함 |
| experiment_tag | “필터링 가능하게” (구현 디테일 없음) | **`experiment_tag_for_preprocess()`로 이력에 자동 저장** | ON/OFF A/B 비교를 DB·모니터에서 바로 가능 |
| metrics 추가 필드 | `preprocessed`, `processed_size_kb` | **+ `original_size_kb`, `preprocess_skipped_reason`** | 원본 크기·fallback 원인 디버깅용 |
| 프론트 UI | 체크박스 + `?preprocess=` | **동일 + 전역 CSS 충돌 수정 (`.form-checkbox-label`)** | `label { display:grid }`, `input { width:100% }` 때문에 체크박스 레이아웃 깨짐 |

### 초안과 동일하게 유지한 것

- 전처리 순서의 핵심: **업/다운스케일(2000/4000/1.5) → 대비 1.5 → 선명도 1.3 → PNG**
- `preprocess` 기본값 **True**, 쿼리 파라미터로 OFF 가능
- Gemini·OpenAI·**Bedrock 공통** 단일 파이프라인 (`article_from_image` 진입점)
- DB 컬럼 `preprocessed`, `processed_image_size_kb`
- 원본 파일/바이트는 디스크에 덮어쓰지 않고 메모리에서만 처리

### 구현하지 않은 것 (초안에도 없음)

- 전처리 결과 이미지 파일 저장·다운로드 UI
- 모니터 페이지에서 `experiment_tag` 전용 필터 UI (컬럼·Excel에는 `experiment_tag` 존재, 전처리 전용 필터는 미구현)
- provider별 다른 전처리 파라미터 (대비/업스케일 계수 통일)

---

## 한 줄 요약 (핸드오프)

초안은 “Pillow로 resize/contrast/sharpen/PNG 후 Vision API” 개념 문서였고, **실제 코드는 zd-article-migrator의 Alembic 0021·15MB 제한·Bedrock·image-convert·OCR 이력/모니터링에 맞춰 `apply_ocr_image_preprocessing` 중심으로 통합 구현**했다. 기능 요구는 충족하며, 차이는 안정성(EXIF/RGB/fallback)과 프로젝트 정합성(마이그레이션 번호·라우터명·적용 범위) 쪽이다.
