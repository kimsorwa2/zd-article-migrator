import { useCallback, useEffect, useRef, useState } from "react";

/** 안내 메시지가 화면에 유지되는 기본 시간(밀리초) */
export const NOTICE_AUTO_DISMISS_MS = 5000;

/** 오류 메시지가 화면에 유지되는 기본 시간(밀리초) */
export const NOTICE_ERROR_DISMISS_MS = 20000;

export type NoticeVariant = "info" | "error";

export interface SetNoticeOptions {
  /** info: 일반 안내, error: 실패·경고 */
  variant?: NoticeVariant;
  /** 자동 숨김까지 대기 시간(밀리초). 생략 시 variant별 기본값 */
  durationMs?: number;
}

/**
 * 일정 시간이 지나면 자동으로 사라지는 안내 메시지 상태를 제공한다.
 * @param durationMs info 메시지 표시 유지 시간(기본 5초)
 */
export function useTimedNotice(durationMs: number = NOTICE_AUTO_DISMISS_MS) {
  const [message, setMessageState] = useState("");
  const [noticeVariant, setNoticeVariant] = useState<NoticeVariant>("info");
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  /**
   * 예약된 자동 숨김 타이머를 해제한다.
   */
  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  /**
   * 안내 메시지를 즉시 비운다.
   */
  const clearMessage = useCallback(() => {
    clearTimer();
    setMessageState("");
    setNoticeVariant("info");
  }, [clearTimer]);

  /**
   * 안내 메시지를 표시하고, 지정 시간 후 자동으로 숨긴다.
   * @param next 표시할 메시지(빈 문자열이면 즉시 숨김)
   * @param options variant·표시 시간 등 옵션
   */
  const setMessage = useCallback(
    (next: string, options?: SetNoticeOptions) => {
      clearTimer();
      setMessageState(next);

      if (next.trim().length === 0) {
        setNoticeVariant("info");
        return;
      }

      const variant = options?.variant ?? "info";
      setNoticeVariant(variant);
      const dismissMs = options?.durationMs ?? (variant === "error" ? NOTICE_ERROR_DISMISS_MS : durationMs);

      timerRef.current = setTimeout(() => {
        setMessageState("");
        setNoticeVariant("info");
        timerRef.current = null;
      }, dismissMs);
    },
    [clearTimer, durationMs],
  );

  useEffect(() => clearTimer, [clearTimer]);

  return { message, noticeVariant, setMessage, clearMessage };
}
