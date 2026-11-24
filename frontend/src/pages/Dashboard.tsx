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
  detected_problem?: {
    reason?: string;
  };
  selected_action?: string;
  safety?: {
    approved?: boolean;
    reason?: string;
  };
  outcome?: string;
};

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
    setH(history.data);
    return {
      state: current.data as Metrics,
      history: history.data as Metrics[],
    };
  }

  useEffect(() => {
    load().catch((err) => {
      console.error("Failed to load resource metrics:", err);
      setError("Unable to load resource metrics. Check the backend connection.");
    });

    const ws = new WebSocket(
      (import.meta.env.VITE_WS_URL || "ws://localhost:8000") + "/ws/metrics"
    );

    ws.onmessage = (event) => {
      try {
        const incoming = JSON.parse(event.data);
        setM((previous) => ({ ...previous, ...incoming }));
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
      const history = snapshot.history.length
        ? snapshot.history
        : [snapshot.state];

      const response = await api.post("/api/agents/run", {
        history,
        state: snapshot.state,
        mode: "simulation",
      });

      setDecision(response.data);
      await load();
    } catch (err) {
      console.error("Agent cycle failed:", err);
      setError("Agent cycle failed. Check the API connection and request details.");
    } finally {
      setRunning(false);
    }
  }

  const cards = [
    ["CPU", m.cpu_percent, "%"],
    ["RAM", m.memory_percent, "%"],
    ["Network", m.network_usage, "%"],
    ["Active Workloads", m.active_workloads, ""],
    ["Instances", m.instances, ""],
    ["Latency", m.latency_ms, "ms"],
    ["Estimated Cost", m.estimated_cost, ""],
    ["Energy", m.estimated_energy, ""],
    ["Agent Status", "READY", ""],
  ];

  return (
    <main>
      <div className="mb-6 flex justify-between">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-slate-500">
            Closed-loop computing resource management
          </p>
        </div>

        <button
          onClick={run}
          disabled={running}
          className="rounded-lg bg-indigo-600 px-5 py-3 text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {running ? "Running Agent..." : "Run Agent Cycle"}
        </button>
      </div>

      {error && (
        <div role="alert" className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="mb-6 grid grid-cols-3 gap-4">
        {cards.map(([label, value, unit]) => (
          <MetricCard
            key={label as string}
            label={label as string}
            value={
              typeof value === "number" ? value.toFixed(1) : value ?? "—"
            }
            unit={unit as string}
          />
        ))}
      </div>

      <section className="rounded-xl border bg-white p-5">
        <h2 className="mb-3 font-semibold">Live Resource Metrics</h2>
        <Chart data={h} keys={["cpu_percent", "memory_percent"]} />
      </section>

      {decision && (
        <section className="mt-5 rounded-xl border bg-white p-5">
          <h2 className="font-semibold">
            Latest Decision: {decision.decision_id}
          </h2>
          <p className="mt-2">
            Problem: {decision.detected_problem?.reason || "No problem detected"}
          </p>
          <p>
            Selected action: <b>{decision.selected_action || "DO_NOTHING"}</b>
          </p>
          <p>
            Safety: {decision.safety?.approved ? "APPROVED" : "REJECTED"}
            {" — "}
            {decision.safety?.reason || "No safety information"}
          </p>
          <p>Outcome: {decision.outcome || "UNKNOWN"}</p>
        </section>
      )}
    </main>
  );
}
