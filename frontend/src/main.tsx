import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import { api } from "./lib/api";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import Experiments from "./pages/Experiments";
import Decisions from "./pages/Decisions";
import Workloads from "./pages/Workloads";
import Predictions from "./pages/Predictions";
import Monitoring from "./pages/Monitoring";
import Optimization from "./pages/Optimization";
import Settings from "./pages/Settings";
import AgentDecisions from "./pages/AgentDecisions";

type RuntimeStatus = {
  connected: boolean;
  simulationMode?: boolean;
  reasoningProvider?: string;
};

function App() {
  const [page, setPage] = useState("Dashboard");
  const [runtime, setRuntime] = useState<RuntimeStatus>({ connected: false });

  useEffect(() => {
    let active = true;
    const check = async () => {
      try {
        const [health, agent] = await Promise.all([
          api.get("/health"),
          api.get("/api/agents/status"),
        ]);
        if (!active) return;
        setRuntime({
          connected: health.data?.status === "ok",
          simulationMode: Boolean(health.data?.simulation_mode),
          reasoningProvider: agent.data?.reasoning_provider || "rule_based",
        });
      } catch {
        if (active) setRuntime({ connected: false });
      }
    };
    check();
    const interval = setInterval(check, 15000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  let content;
  switch (page) {
    case "Dashboard": content = <Dashboard />; break;
    case "Resource Monitoring": content = <Monitoring />; break;
    case "Workloads": content = <Workloads />; break;
    case "Predictions": content = <Predictions />; break;
    case "Agent Decisions": content = <AgentDecisions />; break;
    case "Optimization": content = <Optimization />; break;
    case "Experiments": content = <Experiments />; break;
    case "Decision Logs": content = <Decisions />; break;
    case "Settings": content = <Settings />; break;
    default: content = <Dashboard />;
  }

  return (
    <div className="app-shell">
      <Sidebar page={page} setPage={setPage} />
      <div className="app-main">
        <header className="topbar">
          <div>
            <div className="topbar-kicker">COMPUTE RESOURCE MANAGEMENT</div>
            <div className="topbar-title">Agentic Resource Control Workspace</div>
          </div>
          <div className="topbar-statuses" aria-label="Environment status">
            <span className="topbar-chip">
              <span className="chip-dot" style={{ background: runtime.connected ? "#18a58c" : "#d45c5c" }} />
              {runtime.connected ? (runtime.simulationMode ? "SIMULATION MODE" : "BACKEND ONLINE") : "BACKEND OFFLINE"}
            </span>
            <span className="topbar-chip safety">
              <span className="chip-dot" style={{ background: runtime.connected ? "#18a58c" : "#d45c5c" }} />
              {runtime.connected ? `SAFETY ENABLED · ${runtime.reasoningProvider?.replace(/_/g, " ").toUpperCase()}` : "WAITING FOR API"}
            </span>
          </div>
        </header>
        <div className="page-content">{content}</div>
      </div>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
