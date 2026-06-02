import { useEffect, useState } from "react";
import { apiClient, type Instance } from "./api/client";
import AppSidebar, { type AppRouteKey } from "./components/AppSidebar";
import AiOcrPage from "./pages/AiOcrPage";
import InstancesPage from "./pages/InstancesPage";
import MigratePage from "./pages/MigratePage";
import AiSettingsPage from "./pages/AiSettingsPage";
import ConvertImagePage from "./pages/ConvertImagePage";
import PlaceholderPage from "./pages/PlaceholderPage";

export default function App() {
  const [route, setRoute] = useState<AppRouteKey>("instances");
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
  }, [route]);

  function renderContent() {
    switch (route) {
      case "instances":
        return <InstancesPage />;
      case "ai-settings":
        return <AiSettingsPage />;
      case "migrate-file":
        return (
          <PlaceholderPage
            title="파일로 아티클 이관"
            description="CSV·JSON 등 파일을 업로드해 Zendesk 아티클로 일괄 등록합니다."
          />
        );
      case "migrate-instance":
        return <MigratePage instances={instances} />;
      case "create-image":
        return <AiOcrPage instances={instances} />;
      case "convert-image":
        return <ConvertImagePage instances={instances} />;
      default:
        return <InstancesPage />;
    }
  }

  return (
    <div className="app-shell">
      <AppSidebar activeRoute={route} onNavigate={setRoute} />
      <main className="app-main">{renderContent()}</main>
    </div>
  );
}
