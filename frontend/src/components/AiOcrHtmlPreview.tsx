interface AiOcrHtmlPreviewProps {
  /** Gemini가 생성한 Zendesk 아티클 HTML 본문 */
  htmlBody: string;
}

/** Zendesk 기본 테마와 동일하게 callout div를 p 태그로 정규화한다. */
const CALLOUT_DIV_PATTERN =
  /<div\s+class=["']callout\s+callout-(?:warning|danger)["']\s*>([\s\S]*?)<\/div>/gi;

function normalizeHtmlForPreview(htmlBody: string): string {
  return htmlBody.replace(CALLOUT_DIV_PATTERN, "<p>$1</p>");
}

/**
 * AI가 생성한 html_body를 Zendesk 아티클과 동일하게 HTML로 렌더링한다.
 * @param {AiOcrHtmlPreviewProps} props 컴포넌트 props
 * @param {string} props.htmlBody 아티클 본문 HTML
 * @returns {JSX.Element} HTML 렌더링 미리보기
 */
export default function AiOcrHtmlPreview({ htmlBody }: AiOcrHtmlPreviewProps) {
  if (!htmlBody.trim()) {
    return <p className="muted">본문 내용이 없습니다.</p>;
  }

  const normalizedHtml = normalizeHtmlForPreview(htmlBody);

  return (
    <div
      className="ai-ocr-preview-html"
      // AI-OCR 내부 도구: Zendesk 렌더와 동일하게 html_body 표시
      dangerouslySetInnerHTML={{ __html: normalizedHtml }}
    />
  );
}
