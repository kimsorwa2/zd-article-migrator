import { apiClient, type FetchSyncProgress } from "../api/client";

/** 수집 진행 폴링 간격(ms) */
export const SYNC_POLL_INTERVAL_MS = 1500;

/** idle 상태가 연속으로 유지되면 작업 소실로 간주하는 최대 횟수 */
export const SYNC_POLL_MAX_IDLE_ROUNDS = 3;

/**
 * Help Center 수집이 완료될 때까지 진행률 API를 폴링한다.
 * @param instanceId 수집 대상 인스턴스 ID
 * @param onProgress 폴링마다 호출할 콜백(선택)
 */
export async function waitForSyncCompletion(
  instanceId: number,
  onProgress?: (progress: FetchSyncProgress) => void,
): Promise<FetchSyncProgress> {
  let idleRounds = 0;

  while (true) {
    const progress = await apiClient.getSyncProgress(instanceId);
    onProgress?.(progress);

    if (progress.status === "completed") {
      return progress;
    }
    if (progress.status === "failed") {
      throw new Error(progress.error ?? "Help Center 수집 실패");
    }
    if (progress.status === "running") {
      idleRounds = 0;
    } else if (progress.status === "idle") {
      idleRounds += 1;
      if (idleRounds > SYNC_POLL_MAX_IDLE_ROUNDS) {
        throw new Error("수집 작업 상태를 확인할 수 없습니다. 잠시 후 다시 시도하세요.");
      }
    }

    await new Promise((resolve) => setTimeout(resolve, SYNC_POLL_INTERVAL_MS));
  }
}
