import { useState } from "react";
import { api } from "../lib/api";

type ExperimentRow = {
  system: "BASELINE" | "PROPOSED" | string;
  avg_cpu: number;
  avg_memory: number;
  latency: number;
  throughput: number;
  scaling_actions: number;
  reaction_time: number;
  resource_wastage: number;
  slo_violations: number;
  estimated_cost: number;
  estimated_energy: number;
  prediction_accuracy: number;
  unnecessary_actions: number;
};

const scenarios = [
  "Stable",
  "Increasing",
  "Sudden Spike",
  "Decreasing",
  "Anomaly",
];

function number(value: unknown, digits = 1) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed.toFixed(digits) : "—";
}

export default function Experiments() {
  const [type, setType] = useState("Sudden Spike");
  const [rows, setRows] = useState<ExperimentRow[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function run() {
    setBusy(true);
    setError("");
    setRows([]);

    try {
      const experiment = (
        await api.post("/api/experiments", {
          name: `${type} comparison`,
          workload_type: type,
          duration_seconds: 60,
          seed: 42,
        })
      ).data;

      const response = await api.post(
        `/api/experiments/${experiment.id}/start`
      );

      if (!Array.isArray(response.data) || response.data.length !== 2) {
        throw new Error("The experiment API did not return both systems.");
      }

      setRows(response.data);
    } catch (err) {
      console.error("Experiment comparison failed:", err);
      setError(
        "Unable to run the comparison. Check the backend logs and try again."
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="space-y-5">
      <header>
        <h1 className="text-3xl font-bold">Experiments</h1>
        <p className="mt-1 text-slate-500">
          Compare threshold-based resource management with the agentic
          orchestrator on the same deterministic workload trace.
        </p>
      </header>

      <section className="flex flex-wrap items-center gap-3 rounded-xl border bg-white p-5">
        <label htmlFor="workload-scenario" className="text-sm font-medium">
          Workload scenario
        </label>
        <select
          id="workload-scenario"
          value={type}
          onChange={(event) => setType(event.target.value)}
          disabled={busy}
          className="rounded border p-2"
        >
          {scenarios.map((scenario) => (
            <option key={scenario} value={scenario}>
              {scenario}
            </option>
          ))}
        </select>
        <button
          onClick={run}
          disabled={busy}
          className="rounded-lg bg-indigo-600 px-5 py-2 text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {busy ? "Running comparison..." : "Run Comparison"}
        </button>
        <span className="text-xs text-slate-500">
          Duration: 60 simulated steps · Seed: 42
        </span>
      </section>

      {error && (
        <div
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700"
        >
          {error}
        </div>
      )}

      {busy && (
        <div
          role="status"
          className="rounded-lg border bg-white p-5 text-sm text-slate-600"
        >
          Running both controllers against the same workload trace...
        </div>
      )}

      {rows.length === 2 && (
        <section className="overflow-hidden rounded-xl border bg-white p-5">
          <div className="mb-4">
            <h2 className="font-semibold">
              Results: {type}
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              Values are calculated from simulator output. Lower is generally
              better for latency, cost, energy, wastage, SLO violations and
              unnecessary actions. Higher throughput is generally better.
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[1250px] text-sm">
              <thead>
                <tr className="border-b text-left text-slate-500">
                  <th className="py-3 pr-4">System</th>
                  <th className="px-3 text-right">Avg CPU</th>
                  <th className="px-3 text-right">Avg Memory</th>
                  <th className="px-3 text-right">Latency (ms)</th>
                  <th className="px-3 text-right">Throughput</th>
                  <th className="px-3 text-right">Scaling</th>
                  <th className="px-3 text-right">Reaction (steps)</th>
                  <th className="px-3 text-right">CPU Headroom</th>
                  <th className="px-3 text-right">SLO Violations</th>
                  <th className="px-3 text-right">Cost</th>
                  <th className="px-3 text-right">Energy</th>
                  <th className="px-3 text-right">Forecast Score*</th>
                  <th className="px-3 text-right">Unnecessary Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.system} className="border-b last:border-0">
                    <td className="py-3 pr-4 font-semibold">{row.system}</td>
                    <td className="px-3 text-right">{number(row.avg_cpu)}%</td>
                    <td className="px-3 text-right">{number(row.avg_memory)}%</td>
                    <td className="px-3 text-right">{number(row.latency)}</td>
                    <td className="px-3 text-right">{number(row.throughput)}</td>
                    <td className="px-3 text-right">{row.scaling_actions}</td>
                    <td className="px-3 text-right">{number(row.reaction_time)}</td>
                    <td className="px-3 text-right">{number(row.resource_wastage)}%</td>
                    <td className="px-3 text-right">{row.slo_violations}</td>
                    <td className="px-3 text-right">{number(row.estimated_cost, 3)}</td>
                    <td className="px-3 text-right">{number(row.estimated_energy, 3)}</td>
                    <td className="px-3 text-right">{number(row.prediction_accuracy)}%</td>
                    <td className="px-3 text-right">{row.unnecessary_actions}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="mt-4 text-xs text-slate-500">
            * Forecast Score is the simulator's bounded 100 − MAPE comparison
            score, not a classification accuracy measure. CPU Headroom is
            calculated as 100 − average CPU utilization.
          </p>
        </section>
      )}

      {!busy && rows.length === 0 && !error && (
        <section className="rounded-xl border bg-white p-8 text-center text-sm text-slate-500">
          Choose a workload scenario and run a comparison to see measured
          BASELINE and PROPOSED results.
        </section>
      )}
    </main>
  );
}
