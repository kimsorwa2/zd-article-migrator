# Cursor 작업 프롬프트: AI OCR 호출 모니터링 관리 메뉴

## 목표

관리 대메뉴(사이드바)에 **"AI 호출 이력"** 소메뉴를 추가하고,
관리자가 AI OCR 호출 결과(토큰 수, 지연 시간, 사용 모델, 프롬프트 템플릿 등)를 테이블로 확인할 수 있게 한다.

---

## 작업 범위

### 백엔드

#### 1. Alembic migration 추가
`backend/alembic/versions/0016_ai_ocr_history_metrics.py`

`ai_ocr_analysis_history` 테이블에 다음 컬럼을 추가한다.

```python
op.add_column("ai_ocr_analysis_history", sa.Column("prompt_template_id", sa.Integer(), nullable=True))
op.add_column("ai_ocr_analysis_history", sa.Column("image_size_kb", sa.Integer(), nullable=True))
op.add_column("ai_ocr_analysis_history", sa.Column("latency_ms", sa.Integer(), nullable=True))
op.add_column("ai_ocr_analysis_history", sa.Column("input_tokens", sa.Integer(), nullable=True))
op.add_column("ai_ocr_analysis_history", sa.Column("output_tokens", sa.Integer(), nullable=True))
op.add_column("ai_ocr_analysis_history", sa.Column("thinking_tokens", sa.Integer(), nullable=True))
op.add_column("ai_ocr_analysis_history", sa.Column("finish_reason", sa.String(32), nullable=True))
op.add_column("ai_ocr_analysis_history", sa.Column("parse_success", sa.Boolean(), nullable=True))
op.add_column("ai_ocr_analysis_history", sa.Column("experiment_tag", sa.String(64), nullable=True))
# 비교 분석용 추가 컬럼
op.add_column("ai_ocr_analysis_history", sa.Column("raw_response_text", sa.Text(), nullable=True))
op.add_column("ai_ocr_analysis_history", sa.Column("parse_error_message", sa.Text(), nullable=True))
op.add_column("ai_ocr_analysis_history", sa.Column("used_system_prompt", sa.Text(), nullable=True))
op.add_column("ai_ocr_analysis_history", sa.Column("used_user_prompt", sa.Text(), nullable=True))
```

downgrade는 `op.drop_column`으로 역순 제거.

---

#### 2. `backend/db/models.py` — `AiOcrAnalysisHistory` 모델에 컬럼 추가

```python
prompt_template_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
image_size_kb: Mapped[int | None] = mapped_column(Integer, nullable=True)
latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
thinking_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Gemini thinking only
finish_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
parse_success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
experiment_tag: Mapped[str | None] = mapped_column(String(64), nullable=True)
# 비교 분석용
raw_response_text: Mapped[str | None] = mapped_column(Text, nullable=True)    # AI 원문 (파싱 전)
parse_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)  # 파싱 실패 사유
used_system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)   # 호출 당시 system prompt 스냅샷
used_user_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)     # 호출 당시 user prompt 스냅샷
```

---

#### 3. `backend/services/article_from_image.py` — API 응답에서 metrics 수집

`image_bytes_to_article_gemini` 함수:
- 함수 시작 시점에 `import time` 후 `t_start = time.perf_counter()` 추가
- 응답 처리 후 `result["_metrics"]` dict를 첨부해서 반환:

```python
usage = payload.get("usageMetadata") or {}
result = _finalize_article_result(result)
result["_metrics"] = {
    "input_tokens": usage.get("promptTokenCount"),
    "output_tokens": usage.get("candidatesTokenCount"),
    "thinking_tokens": usage.get("thoughtsTokenCount"),
    "finish_reason": finish_reason,
    "latency_ms": int((time.perf_counter() - t_start) * 1000),
    "raw_response_text": raw_text,   # _parse_article_json_text 호출 전 원문
}
return result
```

`image_bytes_to_article_openai` 함수도 동일하게:

```python
usage = payload.get("usage") or {}
result["_metrics"] = {
    "input_tokens": usage.get("prompt_tokens"),
    "output_tokens": usage.get("completion_tokens"),
    "thinking_tokens": None,
    "finish_reason": choices[0].get("finish_reason"),
    "latency_ms": int((time.perf_counter() - t_start) * 1000),
    "raw_response_text": raw_text,   # _parse_article_json_text 호출 전 원문
}
```

---

#### 4. `backend/services/ai_ocr_service.py` — metrics를 history에 저장

`_get_resolved_prompts` 반환값에 template.id 추가:
```python
# 기존: return template.system_prompt, template.user_prompt
return template.system_prompt, template.user_prompt, template.id
```

`analyze_image` 메서드:
```python
system_prompt, user_prompt, prompt_template_id = await cls._get_resolved_prompts(session)

try:
    result = image_bytes_to_article(
        ...,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )
    metrics = result.pop("_metrics", {})
    parse_success = True
    parse_error_message = None
except (RuntimeError, json.JSONDecodeError) as error:
    # 파싱 실패도 이력에 남긴다
    metrics = {}
    parse_success = False
    parse_error_message = str(error)
    log.error("AI 응답 처리 실패", str(error))
    raise AiOcrServiceError(str(error), log) from error
finally:
    await cls._save_analysis_history(
        session,
        source_filename=filename,
        ai_model=model_id,
        image_size_kb=max(1, len(content) // 1024),
        prompt_template_id=prompt_template_id,
        used_system_prompt=system_prompt,
        used_user_prompt=user_prompt,
        parse_success=parse_success,
        parse_error_message=parse_error_message,
        **metrics,
        **(payload if parse_success else {}),
    )
```

`_save_analysis_history` 시그니처와 `AiOcrAnalysisHistory` 생성 코드에도 새 인자들(`raw_response_text`, `parse_error_message`, `used_system_prompt`, `used_user_prompt`) 반영.

**핵심**: `finally` 블록으로 파싱 성공·실패 모두 이력에 저장한다. 파싱 실패 시에도 `raw_response_text`(AI 원문)와 `parse_error_message`가 남아서 원인 추적이 가능하다.

---

#### 5. `backend/api/schemas.py` — 이력 조회 스키마 확장

`AiOcrAnalysisHistoryItem`에 필드 추가:
```python
prompt_template_id: int | None = None
image_size_kb: int | None = None
latency_ms: int | None = None
input_tokens: int | None = None
output_tokens: int | None = None
thinking_tokens: int | None = None
finish_reason: str | None = None
parse_success: bool | None = None
experiment_tag: str | None = None
raw_response_text: str | None = None
parse_error_message: str | None = None
used_system_prompt: str | None = None
used_user_prompt: str | None = None
```

---

#### 6. `backend/api/routers/ai_ocr.py` — 모니터링 전용 엔드포인트 추가

```python
@router.get("/history/metrics", response_model=AiOcrAnalysisHistoryListResponse)
async def get_ai_ocr_history_metrics(
    limit: int = 100,
    session: AsyncSession = Depends(get_async_session),
) -> AiOcrAnalysisHistoryListResponse:
    """AI OCR 호출 이력 + metrics 조회 (모니터링용)"""
    items = await AiOcrService.list_analysis_history(session, limit=limit)
    return AiOcrAnalysisHistoryListResponse(items=items)
```

`AiOcrService.list_analysis_history`도 새 컬럼들을 반환 dict에 포함시킨다.

---

### 프론트엔드

#### 7. `frontend/src/components/AppSidebar.tsx` — 라우트 및 메뉴 추가

`AppRouteKey`에 `"ai-ocr-monitor"` 추가.

`NAV_GROUPS`의 **"관리"** 그룹에 소메뉴 추가:
```ts
{ id: "ai-ocr-monitor", label: "AI 호출 이력", icon: BarChart2 }
```
아이콘은 `lucide-react`의 `BarChart2` 사용.

`ROUTE_TITLES`에도 추가:
```ts
"ai-ocr-monitor": "AI 호출 이력",
```

---

#### 8. `frontend/src/pages/AiOcrMonitorPage.tsx` — 신규 페이지 생성

- 마운트 시 `GET /api/ai-ocr/history/metrics` 호출
- 결과를 테이블로 렌더링

테이블 컬럼:
| 컬럼 | 설명 |
|------|------|
| 일시 | `created_at` (로컬 시간) |
| 라벨 | `display_label` |
| 모델 | `ai_model` |
| 프롬프트 ID | `prompt_template_id` |
| 이미지 크기 | `image_size_kb` KB |
| 입력 토큰 | `input_tokens` |
| 출력 토큰 | `output_tokens` |
| 추론 토큰 | `thinking_tokens` (없으면 `-`) |
| 지연 시간 | `latency_ms` ms |
| 종료 이유 | `finish_reason` |
| 파싱 성공 | `parse_success` (✅ / ❌ / `-`) |

- 각 행 클릭 시 상세 모달(또는 아코디언) 표시:
  - `used_system_prompt` / `used_user_prompt` — 호출 당시 프롬프트 전문
  - `raw_response_text` — AI 원문 응답 (스크롤 가능한 pre 태그)
  - `parse_error_message` — 파싱 실패 시 에러 메시지
- 상단에 집계 요약 카드(총 호출 수, 평균 입력 토큰, 평균 지연 시간) 표시
- 기존 페이지들의 스타일 패턴을 따름 (별도 CSS 파일 없이 인라인 className 활용)

---

#### 9. `frontend/src/App.tsx` — 라우트 연결

```tsx
import AiOcrMonitorPage from "./pages/AiOcrMonitorPage";

case "ai-ocr-monitor":
  return <AiOcrMonitorPage />;
```

---

## 참고: 기존 코드 패턴

- 백엔드: FastAPI + SQLAlchemy async, Alembic migration
- 프론트엔드: React + TypeScript, `apiClient` (fetch wrapper in `src/api/client.ts`) 사용
- 페이지 컴포넌트 예시: `AiSettingsPage.tsx`, `InstancesPage.tsx` 참고
- 사이드바 메뉴 추가 패턴: `AppSidebar.tsx`의 `NAV_GROUPS` 배열에 항목 추가
- Gemini `usageMetadata` 필드: `promptTokenCount`, `candidatesTokenCount`, `thoughtsTokenCount`
- OpenAI `usage` 필드: `prompt_tokens`, `completion_tokens`
