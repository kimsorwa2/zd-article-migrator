import { X } from "lucide-react";
import type { NoticeVariant } from "../hooks/useTimedNotice";

interface NoticeBannerProps {
  /** 표시할 메시지 */
  message: string;
  /** info: 일반 안내, error: 오류 */
  variant?: NoticeVariant;
  /** 닫기(X) 클릭 시 호출 */
  onDismiss: () => void;
  /** 추가 CSS 클래스 */
  className?: string;
}

/**
 * 상단 안내/오류 메시지를 표시하고 X 버튼으로 닫을 수 있게 한다.
 * @param message 사용자에게 보여줄 문구
 * @param variant 안내 스타일 변형
 * @param onDismiss 닫기 처리 콜백
 * @param className 레이아웃용 추가 클래스
 */
export default function NoticeBanner({ message, variant = "info", onDismiss, className = "" }: NoticeBannerProps) {
  const variantClass = variant === "error" ? "notice-error" : "";

  return (
    <div className={`notice notice-banner ${variantClass} ${className}`.trim()} role={variant === "error" ? "alert" : "status"}>
      <p className="notice-banner-text">{message}</p>
      <button type="button" className="notice-banner-dismiss" onClick={onDismiss} aria-label="알림 닫기">
        <X size={16} aria-hidden="true" />
      </button>
    </div>
  );
}
