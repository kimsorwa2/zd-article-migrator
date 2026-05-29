import type { Instance } from "../api/client";

/**
 * 마이그레이션 화면 인스턴스 선택에 표시할 수 있는지 판별한다.
 * Help Center 수집이 한 번이라도 완료된 인스턴스만 대상으로 한다.
 * @param instance Zendesk 인스턴스
 */
export function isMigrateEligibleInstance(instance: Instance): boolean {
  return instance.is_active && instance.last_fetched_at !== null;
}

/**
 * 타겟 Help Center 브랜드 선택 UI에 노출할 브랜드인지 판별한다.
 * @param brand 수집 상세 브랜드 노드
 */
export function isTargetHelpCenterBrand(brand: { has_help_center: boolean }): boolean {
  return brand.has_help_center;
}
