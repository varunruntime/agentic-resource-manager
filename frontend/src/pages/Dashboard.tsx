import { useEffect, useState } from "react";
import { api } from "../lib/api";
import MetricCard from "../components/MetricCard";
import Chart from "../components/Line";

type Metrics = {
  cpu_percent?: number;
  memory_percent?: number;
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

  async function load() {
    try {
      const current = await api.get("/api/resources/current");
      const history = await api.get("/api/resources/history");

      setM(current.data);
      setH(history.data);
    } catch (error) {
      console.error("Failed to load resource metrics:", error);
    }
  }

  useEffect(() => {
    load();

    const ws = new WebSocket(
      (import.meta.env.VITE_WS_URL || "ws://localhost:8000") +
        "/ws/metrics"
    );

    ws.onmessage = (event) => {
        try {
            const incoming = JSON.parse(event.data);

            setM((previous) => ({
            ...previous,
            ...incoming,
            }));
        } catch (error) {
          console.error("Invalid WebSocket data:", error);
  }
};    

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    return () => {
      ws.close();
    };
  }, []);

  async function run() {
    try {
      const response = await api.post("/api/agents/run?mode=simulation");

      setDecision(response.data);

      // Reload current metrics and history after the agent acts.
      await load();
    } catch (error) {
      console.error("Agent cycle failed:", error);
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
      {/* Header */}
      <div className="flex justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>

          <p className="text-slate-500">
            Closed-loop computing resource management
          </p>
        </div>

        <button
          onClick={run}
          className="bg-indigo-600 text-white px-5 py-3 rounded-lg hover:bg-indigo-700"
        >
          Run Agent Cycle
        </button>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {cards.map(([label, value, unit]) => (
          <MetricCard
            key={label as string}
            label={label as string}
            value={
              typeof value === "number"
                ? value.toFixed(1)
                : value ?? "—"
            }
            unit={unit as string}
          />
        ))}
      </div>

      {/* Live Resource Metrics */}
      <section className="bg-white rounded-xl p-5 border">
        <h2 className="font-semibold mb-3">
          Live Resource Metrics
        </h2>

        <Chart
          data={h}
          keys={["cpu_percent", "memory_percent"]}
        />
      </section>

      {/* Latest Agent Decision */}
      {decision && (
        <section className="bg-white rounded-xl p-5 border mt-5">
          <h2 className="font-semibold">
            Latest Decision: {decision.decision_id}
          </h2>

          <p className="mt-2">
            Problem:{" "}
            {decision.detected_problem?.reason || "No problem detected"}
          </p>

          <p>
            Selected action:{" "}
            <b>{decision.selected_action || "DO_NOTHING"}</b>
          </p>

          <p>
            Safety:{" "}
            {decision.safety?.approved ? "APPROVED" : "REJECTED"}
            {" — "}
            {decision.safety?.reason || "No safety information"}
          </p>

          <p>
            Outcome: {decision.outcome || "UNKNOWN"}
          </p>
        </section>
      )}
    </main>
  );
}