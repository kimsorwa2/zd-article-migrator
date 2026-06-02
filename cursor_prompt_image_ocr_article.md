# Cursor AI 프롬프트 — 이미지 OCR 아티클 생성 메뉴 추가

## 배경 및 목적

현재 Zendesk 아티클 마이그레이션 Python 프로그램이 있음.
이 프로그램에 새로운 메뉴를 추가해야 함.

기능 목표:
1. 사용자가 매뉴얼 이미지를 업로드
2. **Google Gemini Vision API**로 이미지를 분석해 아티클 내용(제목, html_body, 라벨) 자동 생성
3. 생성된 내용을 미리보기로 확인
4. 확인 후 Zendesk 아티클 생성 API 호출

---

## 요청 사항

기존 마이그레이션 프로그램의 메뉴 구조에 아래 기능을 가진 메뉴 항목을 하나 추가해줘.

---

## 추가할 메뉴의 전체 플로우

```
[메뉴 선택]
    ↓
[이미지 파일 경로 입력 또는 파일 선택]
    ↓
[Gemini API 호출 → OCR + 아티클 내용 생성]
    ↓
[미리보기 출력]
  - 제목
  - label_names
  - detected_product
  - maintenance_cycle
  - html_body (터미널에서 읽기 쉽게 출력)
    ↓
[사용자 확인]
  - (y) → Zendesk 아티클 생성 API 호출
  - (e) → 제목 또는 라벨 직접 수정 후 재확인
  - (n) → 취소하고 메뉴로 복귀
    ↓
[생성 완료 → 생성된 아티클 ID 및 URL 출력]
```

---

## Gemini API 호출 코드

아래 코드를 그대로 사용해줘. 수정하지 말 것.

```python
import base64
import httpx
import json
from pathlib import Path

SYSTEM_PROMPT = """
You are a technical writer that converts product manual images into
Zendesk Help Center articles.

The images may come from various products and brands (coffee machines,
appliances, electronics, etc.). Always extract the product name and
context from the image itself — do not assume a fixed product.

Output must be a single JSON object with exactly these fields:
{
  "title": "string",
  "html_body": "string",
  "label_names": ["string"],
  "detected_product": "string",
  "maintenance_cycle": "string or null"
}

Rules for title:
- Format: [제품명] 주요내용 — 부제목
- If product name is not identifiable, use [매뉴얼]
- Concise, under 60 characters
- Written in Korean

Rules for html_body:
- Written in Korean
- Use only: <h3>, <ol>, <ul>, <li>, <p>, <strong>, <div>
- Structure steps as <ol> with <li> per step
- Use <p> for disclaimers, footnotes, and supplementary notices (e.g. "변동될 수 있음", "확정 후 공지")
- For explicit safety/operation warnings inside steps: <div class="callout callout-warning">내용</div>
- For error/danger notices inside steps: <div class="callout callout-danger">내용</div>
- Do NOT wrap section footnotes or prize/event disclaimers in callout — use plain <p>
- Do NOT include <html>, <head>, <body>, <style>, <img> tags
- Preserve all numbered steps in original order
- If multiple sections exist in the image, use <h3> per section
- If a step has a sub-warning, nest the callout inside the <li>

Rules for label_names:
- 3~7 keywords in Korean
- Include: product name, action type, maintenance cycle if found
- No spaces, use hyphens for compounds

Rules for detected_product:
- Brand + model if visible, otherwise brand only, otherwise "unknown"

Rules for maintenance_cycle:
- Extract if mentioned (e.g. "일 1회", "주 1회", "월 1회")
- null if not mentioned

Important:
- Never hallucinate steps not visible in the image
- Output only the JSON object, no markdown fences, no explanation
"""

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

USER_PROMPT = "위 이미지를 분석하여 Zendesk 헬프센터 아티클 JSON으로 변환해줘."


def image_to_article(image_path: str, gemini_api_key: str) -> dict:
    suffix = Path(image_path).suffix.lower()
    media_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(suffix, "image/png")

    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    url = f"{GEMINI_API_BASE}/{GEMINI_MODEL}:generateContent?key={gemini_api_key}"
    response = httpx.post(
        url,
        json={
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"inlineData": {"mimeType": media_type, "data": b64}},
                        {"text": USER_PROMPT},
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 4096,
                "responseMimeType": "application/json",
            },
        },
        timeout=90.0,
    )

    payload = response.json()
    if response.status_code >= 400:
        message = payload.get("error", {}).get("message", response.text)
        raise RuntimeError(f"Gemini API 요청 실패: {message}")

    raw = payload["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(raw)
```

---

## Zendesk 아티클 생성 API

아티클 생성은 아래 스펙으로 호출해줘.
섹션 ID, 카테고리는 사용자가 직접 입력하도록 처리할 것.

```
POST https://{subdomain}.zendesk.com/api/v2/help_center/sections/{section_id}/articles

Headers:
  Authorization: Basic base64({email}/token:{api_token})
  Content-Type: application/json

Body:
{
  "article": {
    "title": "<생성된 제목>",
    "html_body": "<생성된 html_body>",
    "label_names": ["<생성된 라벨들>"],
    "locale": "ko",
    "draft": false
  }
}
```

응답에서 `article.id`와 `article.html_url`을 추출해서 출력해줘.

---

## 미리보기 출력 형식

터미널에서 아래와 같은 형식으로 출력해줘.

```
========================================
[미리보기]
----------------------------------------
제목       : [Jura 커피머신] 일 1회 관리 사항 — 원두 찌꺼기통과 물받이 비우기
감지된 제품 : Jura
관리 주기  : 일 1회
라벨       : jura, 커피머신, 물받이, 일상관리, 매일
----------------------------------------
[본문 미리보기]

(html_body 태그 제거 후 텍스트만 출력)

========================================
이 내용으로 아티클을 생성하시겠습니까?
  (y) 생성    (e) 수정    (n) 취소
>
```

html_body 미리보기는 태그를 제거하고 텍스트만 읽기 좋게 출력할 것.
(Python re 또는 html.parser 사용)

---

## 수정 모드 (e 선택 시)

제목과 라벨만 수정 가능하게 할 것. html_body 수정은 제공하지 않음.

```
수정할 항목을 선택하세요:
  (1) 제목 수정
  (2) 라벨 수정
  (3) 수정 완료 → 미리보기로 돌아가기
>
```

---

## 설정값 처리

**Gemini API Key**, Zendesk subdomain, Zendesk email, Zendesk API token은
기존 프로그램의 설정(config) 관리 방식을 그대로 따를 것.
별도로 새 설정 항목을 추가해야 한다면 기존 방식과 동일한 패턴으로 추가할 것.

Gemini API 키는 [Google AI Studio](https://aistudio.google.com/apikey)에서 발급한다.

---

## 주의사항

- 기존 코드 구조와 스타일을 최대한 유지할 것
- 새로 추가하는 함수는 별도 파일(예: `article_from_image.py`)로 분리할 것
- 기존 메뉴 번호 체계를 깨지 말고 마지막 번호에 이어서 추가할 것
- httpx가 없으면 requests로 대체 가능하나, httpx 우선 사용
- 에러 처리: Gemini API 실패, 파일 없음, 지원하지 않는 확장자, Zendesk API 실패 각각 명확한 에러 메시지 출력
