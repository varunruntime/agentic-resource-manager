import { useState } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
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

function App() {
  const [page, setPage] = useState("Dashboard");

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
            <span className="topbar-chip"><span className="chip-dot" /> SIMULATION MODE</span>
            <span className="topbar-chip safety"><span className="chip-dot" /> SAFETY ENABLED</span>
          </div>
        </header>
        <div className="page-content">{content}</div>
      </div>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
