import { useEffect, useState } from "react";
import { api } from "../lib/api";
import MetricCard from "../components/MetricCard";
import Chart from "../components/Line";

type Metrics = {
  timestamp?: string;
  cpu_percent?: number;
  memory_percent?: number;
  disk_percent?: number;
  network_usage?: number;
  active_workloads?: number;
  instances?: number;
  latency_ms?: number;
  estimated_cost?: number;
  estimated_energy?: number;
};

type Decision = {
  decision_id?: string;
  detected_problem?: { reason?: string };
  selected_action?: string;
  safety?: { approved?: boolean; reason?: string };
  outcome?: string;
};

const pipeline = [
  "Observe", "Analyze", "Predict", "Reason", "Plan",
  "Safety check", "Act", "Evaluate", "Feedback",
];

function display(value: unknown, digits = 1) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed.toFixed(digits) : "—";
}

export default function Dashboard() {
  const [m, setM] = useState<Metrics>({});
  const [h, setH] = useState<Metrics[]>([]);
  const [decision, setDecision] = useState<Decision | undefined>();
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    const [current, history] = await Promise.all([
      api.get("/api/resources/current"),
      api.get("/api/resources/history"),
    ]);
    setM(current.data);
    setH(Array.isArray(history.data) ? history.data : []);
    return {
      state: current.data as Metrics,
      history: (Array.isArray(history.data) ? history.data : []) as Metrics[],
    };
  }

  useEffect(() => {
    load().catch((err) => {
      console.error("Failed to load resource metrics:", err);
      setError("Unable to load resource metrics. Check that the backend is running.");
    });

    const ws = new WebSocket(
      (import.meta.env.VITE_WS_URL || "ws://localhost:8000") + "/ws/metrics"
    );
    ws.onmessage = (event) => {
      try {
        const incoming = JSON.parse(event.data) as Metrics;
        setM((previous) => ({ ...previous, ...incoming }));
        setH((previous) => [...previous, incoming].slice(-100));
      } catch (err) {
        console.error("Invalid WebSocket data:", err);
      }
    };
    ws.onerror = (err) => console.error("WebSocket error:", err);
    return () => ws.close();
  }, []);

  async function run() {
    setRunning(true);
    setError("");
    try {
      const snapshot = await load();
      const history = snapshot.history.length ? snapshot.history : [snapshot.state];
      const response = await api.post("/api/agents/run", {
        history,
        state: snapshot.state,
        mode: "simulation",
      });
      setDecision(response.data);
      await load();
    } catch (err) {
      console.error("Agent cycle failed:", err);
      setError("Agent cycle failed. Check the API connection and backend logs.");
    } finally {
      setRunning(false);
    }
  }

  const cards = [
    { label: "CPU utilization", value: display(m.cpu_percent), unit: "%", symbol: "CPU", detail: "Current compute load" },
    { label: "Memory utilization", value: display(m.memory_percent), unit: "%", symbol: "RAM", detail: "Current memory pressure" },
    { label: "Disk utilization", value: display(m.disk_percent), unit: "%", symbol: "DSK", detail: "Observed disk usage" },
    { label: "Active workloads", value: display(m.active_workloads, 0), unit: "", symbol: "JOB", detail: "Running workload count" },
    { label: "Compute instances", value: display(m.instances, 0), unit: "", symbol: "INS", detail: "Allocated simulator capacity" },
    { label: "Observed latency", value: display(m.latency_ms), unit: "ms", symbol: "LAT", detail: "Latest response-time proxy" },
  ];

  const approved = decision?.safety?.approved;
  const updatedAt = m.timestamp ? new Date(m.timestamp).toLocaleTimeString() : "Awaiting telemetry";

  return (
    <main>
      <header className="page-head">
        <div>
          <div className="page-eyebrow">System overview</div>
          <h1 className="page-title">Resource Dashboard</h1>
          <p className="page-description">
            Monitor simulated infrastructure, inspect resource pressure, and run the closed-loop agent safely.
          </p>
        </div>
        <div className="page-actions">
          <button type="button" onClick={run} disabled={running} className="btn-primary">
            <span aria-hidden="true">↻</span>
            {running ? "Agent running…" : "Run agent cycle"}
          </button>
        </div>
      </header>

      {error && <div role="alert" className="alert alert-error">{error}</div>}

      <div className="status-strip">
        <div className="status-item"><span className="status-pulse" /> <strong>System ready</strong></div>
        <div className="status-item">Execution <strong>Simulation only</strong></div>
        <div className="status-item">Safety policy <strong>Enabled</strong></div>
        <div className="status-item">Latest telemetry <strong>{updatedAt}</strong></div>
      </div>

      <section className="metrics-grid" aria-label="Current resource metrics">
        {cards.map((card) => <MetricCard key={card.label} {...card} />)}
      </section>

      <div className="dashboard-grid">
        <section className="panel panel-pad">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Resource utilization</h2>
              <p className="panel-subtitle">Live CPU and memory observations from the simulator</p>
            </div>
            <div className="chart-legend">
              <span className="legend-item"><span className="legend-swatch" /> CPU</span>
              <span className="legend-item"><span className="legend-swatch teal" /> Memory</span>
            </div>
          </div>
          <Chart data={h} keys={["cpu_percent", "memory_percent"]} />
        </section>

        <section className="panel panel-pad">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">System overview</h2>
              <p className="panel-subtitle">Additional operational indicators</p>
            </div>
          </div>
          <div className="overview-list">
            <div className="overview-row"><span className="overview-label">Network usage</span><span className="overview-value">{display(m.network_usage)}%</span></div>
            <div className="overview-row"><span className="overview-label">Estimated cost</span><span className="overview-value">{display(m.estimated_cost, 3)}</span></div>
            <div className="overview-row"><span className="overview-label">Estimated energy</span><span className="overview-value">{display(m.estimated_energy, 3)}</span></div>
            <div className="overview-row"><span className="overview-label">Allocated instances</span><span className="overview-value">{display(m.instances, 0)}</span></div>
          </div>
          <div className="decision-box">
            <div className="decision-box-label">Latest agent outcome</div>
            <div className="decision-box-action">{decision?.selected_action || "No action executed yet"}</div>
            <div className="decision-box-copy">
              {decision
                ? (decision.detected_problem?.reason || decision.outcome || "Agent cycle completed.")
                : "Run an agent cycle to inspect the selected action and its safety result."}
            </div>
            {decision && (
              <div className={"decision-box-copy " + (approved === true ? "value-good" : approved === false ? "" : "value-neutral")}>
                Safety: {approved === true ? "Approved" : approved === false ? "Rejected" : "Not reported"}{decision.safety?.reason ? " · " + decision.safety.reason : ""}
              </div>
            )}
          </div>
        </section>
      </div>

      <section className="panel pipeline-panel">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">Agentic decision pipeline</h2>
            <p className="panel-subtitle">Nine stages in the closed-loop resource management cycle</p>
          </div>
          <span className="topbar-chip safety"><span className="chip-dot" /> SAFETY GATED</span>
        </div>
        <div className="pipeline-grid">
          {pipeline.map((stage, index) => (
            <div className="pipeline-step" key={stage}>
              <span className="pipeline-number">{String(index + 1).padStart(2, "0")}</span>
              <span className="pipeline-name">{stage}</span>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
