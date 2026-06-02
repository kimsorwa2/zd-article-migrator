"""
Vision AI OCR용 이미지 전처리 (Gemini·OpenAI·Bedrock 공통).
업스케일·대비·선명도·PNG 통일로 밀도 높은 한글 표·매뉴얼 인식률을 높인다.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from PIL import Image, ImageEnhance, ImageOps

logger = logging.getLogger(__name__)

# Vision API 업로드 상한과 동일 (ai_ocr.py MAX_IMAGE_BYTES)
MAX_PROCESSED_BYTES = 15 * 1024 * 1024

# 장변 기준: 이하면 업스케일, 초과면 다운스케일
LONG_EDGE_UPSCALE_THRESHOLD_PX = 2000
LONG_EDGE_MAX_PX = 4000
UPSCALE_FACTOR = 1.5

DEFAULT_CONTRAST_FACTOR = 1.5
DEFAULT_SHARPNESS_FACTOR = 1.3

OUTPUT_MEDIA_TYPE = "image/png"


@dataclass(frozen=True)
class OcrPreprocessResult:
    """전처리 적용 결과."""

    image_bytes: bytes
    media_type: str
    preprocessed: bool
    original_size_kb: int
    processed_size_kb: int | None
    skipped_reason: str | None = None


def _bytes_to_kb(data: bytes) -> int:
    """바이트 크기를 KB(올림)로 반환한다."""
    return max(1, (len(data) + 1023) // 1024)


def _long_edge(img: Image.Image) -> int:
    """이미지 장변 길이를 반환한다."""
    return max(img.size)


def _normalize_size(img: Image.Image) -> Image.Image:
    """
    장변 기준 업스케일/다운스케일. 비율 유지.
    @param img PIL Image
    @returns 크기 조정된 Image
    """
    width, height = img.size
    long_edge = max(width, height)

    if long_edge > LONG_EDGE_MAX_PX:
        scale = LONG_EDGE_MAX_PX / long_edge
    elif long_edge < LONG_EDGE_UPSCALE_THRESHOLD_PX:
        scale = UPSCALE_FACTOR
    else:
        return img

    new_width = max(1, int(round(width * scale)))
    new_height = max(1, int(round(height * scale)))
    return img.resize((new_width, new_height), Image.Resampling.LANCZOS)


def _to_rgb(img: Image.Image) -> Image.Image:
    """Vision API·PNG 저장용 RGB로 변환한다."""
    if img.mode == "RGB":
        return img
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        background = Image.new("RGB", img.size, (255, 255, 255))
        rgba = img.convert("RGBA")
        background.paste(rgba, mask=rgba.split()[-1])
        return background
    return img.convert("RGB")


def _enhance_contrast(img: Image.Image, factor: float = DEFAULT_CONTRAST_FACTOR) -> Image.Image:
    """대비를 강화한다."""
    return ImageEnhance.Contrast(img).enhance(factor)


def _enhance_sharpness(img: Image.Image, factor: float = DEFAULT_SHARPNESS_FACTOR) -> Image.Image:
    """선명도를 강화한다."""
    return ImageEnhance.Sharpness(img).enhance(factor)


def _encode_png(img: Image.Image) -> bytes:
    """PNG bytes로 인코딩한다."""
    buffer = io.BytesIO()
    img.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _run_pipeline(
    image_bytes: bytes,
    *,
    allow_upscale: bool,
) -> bytes:
    """
    전처리 파이프라인을 실행한다.
    @param allow_upscale False면 크기 업스케일만 생략(용량 초과 시 재시도용)
    """
    with Image.open(io.BytesIO(image_bytes)) as opened:
        img = ImageOps.exif_transpose(opened)
        img = _to_rgb(img)

        if allow_upscale:
            img = _normalize_size(img)
        else:
            width, height = img.size
            long_edge = max(width, height)
            if long_edge > LONG_EDGE_MAX_PX:
                scale = LONG_EDGE_MAX_PX / long_edge
                img = img.resize(
                    (max(1, int(round(width * scale))), max(1, int(round(height * scale)))),
                    Image.Resampling.LANCZOS,
                )

        img = _enhance_contrast(img)
        img = _enhance_sharpness(img)
        return _encode_png(img)


def preprocess_for_ocr(image_bytes: bytes, filename: str) -> bytes:
    """
    OCR 정확도 향상을 위한 이미지 전처리(레거시·단순 API).
    @param image_bytes 원본 이미지
    @param filename 로그용 파일명
    @returns 전처리된 PNG bytes
    """
    del filename  # apply_ocr_image_preprocessing에서 일괄 처리
    return _run_pipeline(image_bytes, allow_upscale=True)


def preprocess_metrics(original: bytes, processed: bytes) -> dict[str, int | float]:
    """
    전처리 전후 크기 metrics.
    @returns original_size_kb, processed_size_kb, size_ratio
    """
    original_kb = _bytes_to_kb(original)
    processed_kb = _bytes_to_kb(processed)
    ratio = processed_kb / original_kb if original_kb else 1.0
    return {
        "original_size_kb": original_kb,
        "processed_size_kb": processed_kb,
        "size_ratio": round(ratio, 3),
    }


def apply_ocr_image_preprocessing(
    image_bytes: bytes,
    media_type: str,
    filename: str,
    *,
    enabled: bool = True,
) -> OcrPreprocessResult:
    """
    Vision OCR 호출 전 이미지 전처리를 적용한다.
    Gemini·OpenAI·Bedrock 모두 동일 파이프라인을 사용한다.

    @param enabled False면 원본 그대로 반환
    @returns OcrPreprocessResult
    """
    original_kb = _bytes_to_kb(image_bytes)
    if not enabled:
        return OcrPreprocessResult(
            image_bytes=image_bytes,
            media_type=media_type,
            preprocessed=False,
            original_size_kb=original_kb,
            processed_size_kb=None,
            skipped_reason="disabled",
        )

    skip_reason: str | None = None
    try:
        processed = _run_pipeline(image_bytes, allow_upscale=True)
        if len(processed) > MAX_PROCESSED_BYTES:
            logger.info(
                "OCR 전처리 1차 용량 초과(%sKB) — 업스케일 없이 재시도 | file=%s",
                _bytes_to_kb(processed),
                filename,
            )
            processed = _run_pipeline(image_bytes, allow_upscale=False)
            if len(processed) > MAX_PROCESSED_BYTES:
                skip_reason = "size_limit"
                processed = image_bytes
    except Exception as error:
        logger.warning("OCR 전처리 실패 — 원본 사용 | file=%s | %s", filename, error)
        skip_reason = "error"
        processed = image_bytes

    if skip_reason:
        return OcrPreprocessResult(
            image_bytes=image_bytes,
            media_type=media_type,
            preprocessed=False,
            original_size_kb=original_kb,
            processed_size_kb=None,
            skipped_reason=skip_reason,
        )

    processed_kb = _bytes_to_kb(processed)
    logger.info(
        "OCR 전처리 완료 | file=%s | %sKB → %sKB",
        filename,
        original_kb,
        processed_kb,
    )
    return OcrPreprocessResult(
        image_bytes=processed,
        media_type=OUTPUT_MEDIA_TYPE,
        preprocessed=True,
        original_size_kb=original_kb,
        processed_size_kb=processed_kb,
        skipped_reason=None,
    )


def experiment_tag_for_preprocess(preprocessed: bool) -> str:
    """모니터링 A/B 비교용 experiment_tag."""
    return "preprocess_on" if preprocessed else "preprocess_off"
