/** 프롬프트 셀렉트·목록 표시용 최소 필드 */
export interface AiOcrPromptLabelSource {
  id: number;
  name: string;
  is_builtin?: boolean;
  description?: string | null;
}

/**
 * 프롬프트 템플릿을 셀렉트 옵션 라벨로 포맷한다 (이름 중복 허용, ID로 구분).
 * @param template 프롬프트 템플릿
 * @returns 예: #3 · 가전 매뉴얼용 · 기본
 */
export function formatAiOcrPromptLabel(template: AiOcrPromptLabelSource): string {
  const parts = [`#${template.id}`, template.name];
  if (template.is_builtin) {
    parts.push("기본");
  }
  return parts.join(" · ");
}
