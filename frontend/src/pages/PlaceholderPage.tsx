import type { LucideIcon } from "lucide-react";
import { Construction } from "lucide-react";

interface PlaceholderPageProps {
  /** 페이지 제목 */
  title: string;
  /** 안내 문구 */
  description: string;
  /** 상단 아이콘 */
  icon?: LucideIcon;
}

/**
 * 아직 구현되지 않은 메뉴용 플레이스홀더 페이지.
 * @param title 페이지 제목
 * @param description 사용자 안내 문구
 * @param icon 제목 옆 아이콘
 */
export default function PlaceholderPage({
  title,
  description,
  icon: Icon = Construction,
}: PlaceholderPageProps) {
  return (
    <section className="page placeholder-page">
      <header className="page-top">
        <h2 className="page-title">
          <Icon size={24} aria-hidden="true" />
          {title}
        </h2>
        <p className="page-lead">{description}</p>
      </header>

      <div className="placeholder-card">
        <div className="placeholder-card-icon" aria-hidden="true">
          <Construction size={32} />
        </div>
        <h3>준비 중입니다</h3>
        <p className="muted">해당 기능은 곧 제공될 예정입니다. 먼저 다른 메뉴를 이용해 주세요.</p>
      </div>
    </section>
  );
}
