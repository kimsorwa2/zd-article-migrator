"""
AI-OCR API 호출 요청·응답 작업 로그 수집.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

AiOcrLogLevel = Literal["info", "error", "success"]


@dataclass
class AiOcrLogEntry:
    """
    /**
     * 프론트 작업 로그 한 건.
     */
    """

    timestamp: str
    level: AiOcrLogLevel
    summary: str
    body: str

    def to_dict(self) -> dict[str, str]:
        return {
            "timestamp": self.timestamp,
            "level": self.level,
            "summary": self.summary,
            "body": self.body,
        }


class AiOcrLogCollector:
    """
    /**
     * AI-OCR 단계별 요청·응답 전문을 누적한다.
     */
    """

    def __init__(self) -> None:
        self._entries: list[AiOcrLogEntry] = []

    def _now_label(self) -> str:
        return datetime.now(UTC).strftime("%H:%M:%S")

    def add(self, level: AiOcrLogLevel, summary: str, body: str) -> None:
        self._entries.append(
            AiOcrLogEntry(
                timestamp=self._now_label(),
                level=level,
                summary=summary,
                body=body.strip(),
            )
        )

    def info(self, summary: str, body: str) -> None:
        self.add("info", summary, body)

    def success(self, summary: str, body: str) -> None:
        self.add("success", summary, body)

    def error(self, summary: str, body: str) -> None:
        self.add("error", summary, body)

    def extend(self, other: AiOcrLogCollector) -> None:
        self._entries.extend(other._entries)

    def to_list(self) -> list[dict[str, str]]:
        return [entry.to_dict() for entry in self._entries]

    @staticmethod
    def format_json(data: Any) -> str:
        """
        /**
         * JSON을 읽기 쉽게 들여쓰기한다.
         */
        """
        try:
            return json.dumps(data, ensure_ascii=False, indent=2)
        except (TypeError, ValueError):
            return str(data)


class AiOcrServiceError(Exception):
    """
    /**
     * AI-OCR 처리 실패 시 작업 로그를 함께 전달한다.
     */
    """

    def __init__(self, message: str, logs: AiOcrLogCollector) -> None:
        super().__init__(message)
        self.logs = logs
