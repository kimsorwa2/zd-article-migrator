from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import (
    AiOcrAnalysisHistoryListResponse,
    AiOcrAnalyzeResponse,
    AiOcrCreateArticleRequest,
    AiOcrCreateArticleResponse,
    AiOcrPromptTemplateCreateRequest,
    AiOcrPromptTemplateResponse,
    AiOcrPromptTemplateUpdateRequest,
    AiOcrModelOptionsResponse,
    AiOcrSettingsResponse,
    AiOcrSettingsUpdateRequest,
)
from db.database import get_async_session
from services.ai_model_options import list_models_for_api
from services.ai_ocr_log import AiOcrServiceError
from services.ai_ocr_service import AiOcrService

router = APIRouter(prefix="/ai-ocr", tags=["ai-ocr"])

MAX_IMAGE_BYTES = 15 * 1024 * 1024


def _http_error(
    *,
    status_code: int,
    message: str,
    logs: list[dict[str, str]] | None = None,
) -> HTTPException:
    """
    /**
     * 프론트 작업 로그와 함께 HTTP 오류를 반환한다.
     */
    """
    detail: dict[str, object] = {"message": message}
    if logs:
        detail["logs"] = logs
    return HTTPException(status_code=status_code, detail=detail)


@router.get("/model-options", response_model=AiOcrModelOptionsResponse)
async def get_ai_ocr_model_options() -> AiOcrModelOptionsResponse:
    """
    /**
     * Vision OCR에 사용 가능한 모델 셀렉트 옵션을 반환한다.
     */
    """
    return AiOcrModelOptionsResponse.model_validate(list_models_for_api())


@router.get("/settings", response_model=AiOcrSettingsResponse)
async def get_ai_ocr_settings(session: AsyncSession = Depends(get_async_session)) -> AiOcrSettingsResponse:
    """
    /**
     * Gemini AI-OCR 설정을 조회한다.
     */
    """
    data = await AiOcrService.get_settings(session)
    return AiOcrSettingsResponse.model_validate(data)


@router.put("/settings", response_model=AiOcrSettingsResponse)
async def update_ai_ocr_settings(
    payload: AiOcrSettingsUpdateRequest,
    session: AsyncSession = Depends(get_async_session),
) -> AiOcrSettingsResponse:
    """
    /**
     * Gemini 계정명·API 키를 저장한다.
     */
    """
    try:
        data = await AiOcrService.save_settings(
            session,
            active_provider=payload.active_provider,
            gemini_account=payload.gemini_account,
            gemini_api_key=payload.gemini_api_key,
            openai_account=payload.openai_account,
            openai_api_key=payload.openai_api_key,
            gemini_model=payload.gemini_model,
            openai_model=payload.openai_model,
            active_prompt_id=payload.active_prompt_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    return AiOcrSettingsResponse.model_validate(data)


@router.get("/prompts", response_model=list[AiOcrPromptTemplateResponse])
async def list_ai_ocr_prompts(session: AsyncSession = Depends(get_async_session)) -> list[AiOcrPromptTemplateResponse]:
    """
    /**
     * 저장된 OCR 프롬프트 템플릿 목록을 조회한다.
     */
    """
    items = await AiOcrService.list_prompt_templates(session)
    return [AiOcrPromptTemplateResponse.model_validate(item) for item in items]


@router.post("/prompts", response_model=AiOcrPromptTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_ai_ocr_prompt(
    payload: AiOcrPromptTemplateCreateRequest,
    session: AsyncSession = Depends(get_async_session),
) -> AiOcrPromptTemplateResponse:
    """
    /**
     * 새 OCR 프롬프트 템플릿을 저장한다.
     */
    """
    try:
        data = await AiOcrService.create_prompt_template(
            session,
            name=payload.name,
            description=payload.description,
            system_prompt=payload.system_prompt,
            user_prompt=payload.user_prompt,
            set_active=payload.set_active,
        )
    except ValueError as error:
        raise _http_error(status_code=status.HTTP_400_BAD_REQUEST, message=str(error)) from error
    return AiOcrPromptTemplateResponse.model_validate(data)


@router.put("/prompts/{template_id}", response_model=AiOcrPromptTemplateResponse)
async def update_ai_ocr_prompt(
    template_id: int,
    payload: AiOcrPromptTemplateUpdateRequest,
    session: AsyncSession = Depends(get_async_session),
) -> AiOcrPromptTemplateResponse:
    """
    /**
     * OCR 프롬프트 템플릿을 수정한다.
     */
    """
    try:
        data = await AiOcrService.update_prompt_template(
            session,
            template_id=template_id,
            name=payload.name,
            description=payload.description,
            system_prompt=payload.system_prompt,
            user_prompt=payload.user_prompt,
        )
    except ValueError as error:
        raise _http_error(status_code=status.HTTP_400_BAD_REQUEST, message=str(error)) from error
    return AiOcrPromptTemplateResponse.model_validate(data)


@router.delete("/prompts/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ai_ocr_prompt(
    template_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> None:
    """
    /**
     * OCR 프롬프트 템플릿을 삭제한다(내장 기본 템플릿 제외).
     */
    """
    try:
        await AiOcrService.delete_prompt_template(session, template_id=template_id)
    except ValueError as error:
        raise _http_error(status_code=status.HTTP_400_BAD_REQUEST, message=str(error)) from error


@router.get("/history", response_model=AiOcrAnalysisHistoryListResponse)
async def list_ai_ocr_history(session: AsyncSession = Depends(get_async_session)) -> AiOcrAnalysisHistoryListResponse:
    """
    /**
     * 저장된 OCR 분석 이력을 조회한다(미리보기 복원용).
     */
    """
    items = await AiOcrService.list_analysis_history(session)
    return AiOcrAnalysisHistoryListResponse.model_validate({"items": items})


@router.post("/analyze", response_model=AiOcrAnalyzeResponse)
async def analyze_manual_image(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_async_session),
) -> AiOcrAnalyzeResponse:
    """
    /**
     * 매뉴얼 이미지를 Google Gemini Vision으로 분석해 아티클 초안을 생성한다.
     */
    """
    if not file.filename:
        raise _http_error(status_code=status.HTTP_400_BAD_REQUEST, message="파일명이 없습니다.")

    content = await file.read()
    if not content:
        raise _http_error(status_code=status.HTTP_400_BAD_REQUEST, message="빈 파일입니다.")
    if len(content) > MAX_IMAGE_BYTES:
        raise _http_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="이미지 크기는 15MB 이하여야 합니다.",
        )

    try:
        result = await AiOcrService.analyze_image(
            session,
            filename=file.filename,
            content=content,
        )
    except AiOcrServiceError as error:
        raise _http_error(
            status_code=status.HTTP_502_BAD_GATEWAY,
            message=str(error),
            logs=error.logs.to_list(),
        ) from error
    except FileNotFoundError as error:
        raise _http_error(status_code=status.HTTP_400_BAD_REQUEST, message=str(error)) from error

    return AiOcrAnalyzeResponse.model_validate(result)


@router.post("/create-article", response_model=AiOcrCreateArticleResponse)
async def create_article_from_ocr(
    payload: AiOcrCreateArticleRequest,
    session: AsyncSession = Depends(get_async_session),
) -> AiOcrCreateArticleResponse:
    """
    /**
     * 분석·확인된 내용으로 Zendesk Help Center 아티클을 생성한다.
     */
    """
    try:
        result = await AiOcrService.create_zendesk_article(
            session,
            instance_id=payload.instance_id,
            brand_id=payload.brand_id,
            section_a_id=payload.section_a_id,
            title=payload.title,
            html_body=payload.html_body,
            label_names=payload.label_names,
            locale=payload.locale,
            draft=payload.draft,
        )
    except AiOcrServiceError as error:
        raise _http_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=str(error),
            logs=error.logs.to_list(),
        ) from error

    return AiOcrCreateArticleResponse.model_validate(result)
