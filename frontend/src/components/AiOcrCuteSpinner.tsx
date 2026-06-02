import { Sparkles } from "lucide-react";

interface AiOcrCuteSpinnerProps {
  /** 스피너 아래에 표시할 안내 문구 */
  message?: string;
  /** 보조 안내 (작은 글씨) */
  hint?: string;
}

/**
 * OCR 분석 대기 중 미리보기 영역에 쓰는 귀여운 로딩 스피너.
 */
export default function AiOcrCuteSpinner({
  message = "AI가 이미지를 분석하고 있어요...",
  hint = "잠시만 기다려 주세요",
}: AiOcrCuteSpinnerProps) {
  return (
    <div className="ai-ocr-cute-spinner-wrap" role="status" aria-live="polite" aria-busy="true">
      <div className="ai-ocr-cute-spinner" aria-hidden="true">
        <span className="ai-ocr-cute-spinner-orbit" />
        <Sparkles className="ai-ocr-cute-spinner-icon" size={28} strokeWidth={1.75} />
        <div className="ai-ocr-cute-spinner-dots">
          <span />
          <span />
          <span />
        </div>
      </div>
      <p className="ai-ocr-cute-spinner-message">{message}</p>
      {hint ? <p className="muted ai-ocr-cute-spinner-hint">{hint}</p> : null}
    </div>
  );
}
