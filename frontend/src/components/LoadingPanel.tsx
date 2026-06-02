import { Loader2 } from "lucide-react";

interface LoadingPanelProps {
  /** 로딩 안내 문구 */
  message: string;
  /** panel: 카드형 영역, inline: 컴팩트 표시 */
  variant?: "panel" | "inline";
  /** false면 스피너 없이 메시지·프로그레스 바만 표시 */
  showSpinner?: boolean;
}

/**
 * 로딩 중 상태를 스피너와 진행 바 애니메이션으로 표시한다.
 * @param message 사용자에게 보여줄 로딩 메시지
 * @param variant 레이아웃 크기 변형
 * @param showSpinner 스피너 표시 여부
 */
export default function LoadingPanel({
  message,
  variant = "panel",
  showSpinner = true,
}: LoadingPanelProps) {
  return (
    <div className={`loading-panel loading-panel-${variant}`} role="status" aria-live="polite" aria-busy="true">
      {showSpinner ? (
        <Loader2 className="loading-panel-spinner" size={variant === "panel" ? 32 : 24} aria-hidden="true" />
      ) : null}
      <p className="loading-panel-message">{message}</p>
      <div className="loading-panel-track" aria-hidden="true">
        <div className="loading-panel-bar" />
      </div>
    </div>
  );
}
