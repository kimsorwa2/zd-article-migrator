import { useEffect, useState } from "react";
import { Database, Rocket } from "lucide-react";
import { apiClient, type Instance } from "./api/client";
import InstancesPage from "./pages/InstancesPage";
import MigratePage from "./pages/MigratePage";

type TabKey = "instances" | "migrate";

export default function App() {
  const [tab, setTab] = useState<TabKey>("instances");
  const [instances, setInstances] = useState<Instance[]>([]);

  useEffect(() => {
    async function loadInstances() {
      try {
        const data = await apiClient.listInstances();
        setInstances(data);
      } catch {
        setInstances([]);
      }
    }
    void loadInstances();
  }, [tab]);

  return (
    <main className="app">
      <div className="layout">
        <aside className="sidebar">
          <p className="kicker">Zendesk Article Migration Console</p>
          <h1 className="sidebar-title">
            <span className="sidebar-title-line">젠데스크 아티클</span>
            <span className="sidebar-title-line">마이그레이션</span>
          </h1>
          <nav className="sidebar-nav">
            <button type="button" className={tab === "instances" ? "active-tab" : ""} onClick={() => setTab("instances")}>
              <Database className="menu-icon" size={16} aria-hidden="true" />
              인스턴스 관리
            </button>
            <button type="button" className={tab === "migrate" ? "active-tab" : ""} onClick={() => setTab("migrate")}>
              <Rocket className="menu-icon" size={16} aria-hidden="true" />
              마이그레이션
            </button>
          </nav>
          <div className="sidebar-footer">
            <p className="sidebar-footer-label">Developer</p>
            <p className="sidebar-footer-name">Sora Kim</p>
            <a className="sidebar-footer-email" href="mailto:kimsorwa@gmail.com">
              kimsorwa@gmail.com
            </a>
          </div>
        </aside>

        <section className="content">
          {tab === "instances" ? <InstancesPage /> : null}
          {tab === "migrate" ? <MigratePage instances={instances} /> : null}
        </section>
      </div>
    </main>
  );
}
