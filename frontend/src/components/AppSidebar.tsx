import type { LucideIcon } from "lucide-react";
import {
  ArrowLeftRight,
  BarChart2,
  Bot,
  MessageSquareText,
  FileUp,
  Layers3,
  RefreshCw,
  ScanText,
  Server,
} from "lucide-react";

/** 앱 라우트 키 */
export type AppRouteKey =
  | "instances"
  | "ai-settings"
  | "ai-prompts"
  | "ai-ocr-monitor"
  | "migrate-file"
  | "migrate-instance"
  | "create-image"
  | "convert-image";

interface NavItem {
  id: AppRouteKey;
  label: string;
  icon: LucideIcon;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

interface AppSidebarProps {
  activeRoute: AppRouteKey;
  onNavigate: (route: AppRouteKey) => void;
}

/** 사이드바 대·소메뉴 구조 */
const NAV_GROUPS: NavGroup[] = [
  {
    label: "관리",
    items: [
      { id: "instances", label: "인스턴스 관리", icon: Server },
      { id: "ai-settings", label: "AI 설정", icon: Bot },
      { id: "ai-prompts", label: "프롬프트 관리", icon: MessageSquareText },
      { id: "ai-ocr-monitor", label: "AI 호출 이력", icon: BarChart2 },
    ],
  },
  {
    label: "아티클 마이그레이션",
    items: [
      { id: "migrate-file", label: "파일로 아티클 이관", icon: FileUp },
      { id: "migrate-instance", label: "인스턴스 간 이관", icon: ArrowLeftRight },
    ],
  },
  {
    label: "아티클 생성",
    items: [
      { id: "create-image", label: "이미지로 아티클 생성", icon: ScanText },
      { id: "convert-image", label: "이미지 아티클 변환", icon: RefreshCw },
    ],
  },
];

/**
 * 앱 좌측 사이드바(대메뉴·소메뉴 네비게이션).
 * @param activeRoute 현재 선택된 라우트
 * @param onNavigate 라우트 변경 콜백
 */
export default function AppSidebar({ activeRoute, onNavigate }: AppSidebarProps) {
  return (
    <aside className="app-sidebar">
      <div className="app-sidebar-brand">
        <span className="app-sidebar-logo" aria-hidden="true">
          <Layers3 size={22} />
        </span>
        <div className="app-sidebar-brand-text">
          <strong>Article Console</strong>
          <span>Zendesk Help Center</span>
        </div>
      </div>

      <nav className="app-sidebar-nav" aria-label="주 메뉴">
        {NAV_GROUPS.map((group) => (
          <div key={group.label} className="nav-group">
            <p className="nav-group-label">{group.label}</p>
            <ul className="nav-group-list">
              {group.items.map((item) => {
                const Icon = item.icon;
                const isActive = activeRoute === item.id;
                return (
                  <li key={item.id}>
                    <button
                      type="button"
                      className={`nav-item${isActive ? " nav-item-active" : ""}`}
                      aria-current={isActive ? "page" : undefined}
                      onClick={() => onNavigate(item.id)}
                    >
                      <span className="nav-item-icon" aria-hidden="true">
                        <Icon size={18} />
                      </span>
                      <span className="nav-item-label">{item.label}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      <div className="app-sidebar-footer">
        <p className="app-sidebar-footer-label">Developer</p>
        <p className="app-sidebar-footer-name">Sora Kim</p>
        <a className="app-sidebar-footer-email" href="mailto:kimsorwa@gmail.com">
          kimsorwa@gmail.com
        </a>
      </div>
    </aside>
  );
}

/** 라우트별 페이지 제목(콘텐츠 영역 헤더용) */
export const ROUTE_TITLES: Record<AppRouteKey, string> = {
  instances: "인스턴스 관리",
  "ai-settings": "AI 설정",
  "ai-prompts": "프롬프트 관리",
  "ai-ocr-monitor": "AI 호출 이력",
  "migrate-file": "파일로 아티클 이관",
  "migrate-instance": "인스턴스 간 이관",
  "create-image": "이미지로 아티클 생성",
  "convert-image": "이미지 아티클 변환",
};
