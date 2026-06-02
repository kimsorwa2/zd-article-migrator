from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import (
    ImageConvertAnalyzeRequest,
    ImageConvertAnalyzeResponse,
    ImageConvertArticleDetailResponse,
    ImageConvertArticleListResponse,
)
from db.database import get_async_session
from services.ai_ocr_log import AiOcrServiceError
from services.image_convert_service import ImageConvertService

router = APIRouter(prefix="/image-convert", tags=["image-convert"])
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


@router.get("/articles", response_model=ImageConvertArticleListResponse)
async def list_image_convert_articles(
    source_instance_id: int = Query(..., description="소스 인스턴스 ID"),
    q: str | None = Query(default=None, description="제목 검색"),
    session: AsyncSession = Depends(get_async_session),
) -> ImageConvertArticleListResponse:
    """
    /**
     * 본문에 이미지가 포함된 소스 아티클 목록을 조회한다.
     */
    """
    try:
        items = await ImageConvertService.list_image_articles(
            session,
            source_instance_id=source_instance_id,
            query=q,
        )
    except ValueError as error:
        raise _http_error(status_code=status.HTTP_400_BAD_REQUEST, message=str(error)) from error
    return ImageConvertArticleListResponse.model_validate({"items": items})


@router.get("/articles/{article_id}", response_model=ImageConvertArticleDetailResponse)
async def get_image_convert_article_detail(
    article_id: int,
    source_instance_id: int = Query(..., description="소스 인스턴스 ID"),
    session: AsyncSession = Depends(get_async_session),
) -> ImageConvertArticleDetailResponse:
    """
    /**
     * 선택한 소스 아티클 상세와 본문 이미지 목록을 조회한다.
     */
    """
    try:
        data = await ImageConvertService.get_article_detail(
            session,
            source_instance_id=source_instance_id,
            article_id=article_id,
        )
    except ValueError as error:
        raise _http_error(status_code=status.HTTP_400_BAD_REQUEST, message=str(error)) from error
    return ImageConvertArticleDetailResponse.model_validate(data)


@router.get("/articles/{article_id}/images/{image_index}")
async def get_image_convert_article_image_preview(
    article_id: int,
    image_index: int,
    source_instance_id: int = Query(..., description="소스 인스턴스 ID"),
    session: AsyncSession = Depends(get_async_session),
) -> Response:
    """
    /**
     * 아티클 본문 이미지 미리보기 바이너리를 반환한다.
     */
    """
    try:
        binary, content_type = await ImageConvertService.get_image_preview_bytes(
            session,
            source_instance_id=source_instance_id,
            article_id=article_id,
            image_index=image_index,
        )
    except ValueError as error:
        raise _http_error(status_code=status.HTTP_400_BAD_REQUEST, message=str(error)) from error
    except Exception as error:
        raise _http_error(
            status_code=status.HTTP_502_BAD_GATEWAY,
            message=f"이미지 미리보기를 불러오지 못했습니다: {error}",
        ) from error

    return Response(content=binary, media_type=content_type)


@router.post("/analyze", response_model=ImageConvertAnalyzeResponse)
async def analyze_image_convert_article(
    payload: ImageConvertAnalyzeRequest,
    session: AsyncSession = Depends(get_async_session),
) -> ImageConvertAnalyzeResponse:
    """
    /**
     * 소스 아티클 본문 이미지를 AI-OCR 분석해 타겟 생성용 초안을 만든다.
     */
    """
    try:
        result = await ImageConvertService.analyze_article(
            session,
            source_instance_id=payload.source_instance_id,
            article_id=payload.article_id,
        )
    except AiOcrServiceError as error:
        raise _http_error(
            status_code=status.HTTP_502_BAD_GATEWAY,
            message=str(error),
            logs=error.logs.to_list(),
        ) from error
    except ValueError as error:
        if isinstance(error, json.JSONDecodeError):
            raise _http_error(
                status_code=status.HTTP_502_BAD_GATEWAY,
                message=f"AI 응답 JSON 파싱에 실패했습니다: {error}",
            ) from error
        raise _http_error(status_code=status.HTTP_400_BAD_REQUEST, message=str(error)) from error

    return ImageConvertAnalyzeResponse.model_validate(result)


@router.post("/analyze-with-files", response_model=ImageConvertAnalyzeResponse)
async def analyze_image_convert_article_with_files(
    source_instance_id: int = Form(..., description="소스 인스턴스 ID"),
    article_id: int = Form(..., description="소스 아티클 ID"),
    image_indices: str = Form(
        ...,
        description="업로드 파일이 대체할 본문 이미지 인덱스(쉼표 구분, 예: 0 또는 0,1)",
    ),
    files: list[UploadFile] = File(..., description="로컬 이미지 파일(인덱스 순서와 동일)"),
    session: AsyncSession = Depends(get_async_session),
) -> ImageConvertAnalyzeResponse:
    """
    /**
     * Zendesk에서 받을 수 없는 붙여넣기 이미지를 로컬 파일로 대체해 OCR 분석한다.
     */
    """
    index_parts = [part.strip() for part in image_indices.split(",") if part.strip()]
    if not index_parts:
        raise _http_error(status_code=status.HTTP_400_BAD_REQUEST, message="image_indices가 비어 있습니다.")
    try:
        indices = [int(part) for part in index_parts]
    except ValueError as error:
        raise _http_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="image_indices는 정수 목록이어야 합니다.",
        ) from error

    if len(indices) != len(files):
        raise _http_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="image_indices 개수와 files 개수가 일치해야 합니다.",
        )

    overrides: dict[int, tuple[bytes, str, str]] = {}
    for index, upload in zip(indices, files, strict=True):
        if not upload.filename:
            raise _http_error(status_code=status.HTTP_400_BAD_REQUEST, message="파일명이 없습니다.")
        content = await upload.read()
        if not content:
            raise _http_error(status_code=status.HTTP_400_BAD_REQUEST, message="빈 파일입니다.")
        if len(content) > MAX_IMAGE_BYTES:
            raise _http_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="이미지 크기는 15MB 이하여야 합니다.",
            )
        content_type = upload.content_type or "application/octet-stream"
        overrides[index] = (content, upload.filename, content_type)

    try:
        result = await ImageConvertService.analyze_article(
            session,
            source_instance_id=source_instance_id,
            article_id=article_id,
            image_overrides=overrides,
        )
    except AiOcrServiceError as error:
        raise _http_error(
            status_code=status.HTTP_502_BAD_GATEWAY,
            message=str(error),
            logs=error.logs.to_list(),
        ) from error
    except ValueError as error:
        if isinstance(error, json.JSONDecodeError):
            raise _http_error(
                status_code=status.HTTP_502_BAD_GATEWAY,
                message=f"AI 응답 JSON 파싱에 실패했습니다: {error}",
            ) from error
        raise _http_error(status_code=status.HTTP_400_BAD_REQUEST, message=str(error)) from error

    return ImageConvertAnalyzeResponse.model_validate(result)
