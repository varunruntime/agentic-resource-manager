import { useEffect, useState } from "react";
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
type ExperimentSummary = {
  id: number; name: string; workload_type: string; duration_seconds: number; seed: number; status: string;
};

const scenarios = ["Stable", "Increasing", "Sudden Spike", "Decreasing", "Anomaly"];
function number(value: unknown, digits = 1) {
  if (value === null || value === undefined || value === "") return "—";
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed.toFixed(digits) : "—";
}

export default function Experiments() {
  const [type, setType] = useState("Sudden Spike");
  const [duration, setDuration] = useState(60);
  const [seed, setSeed] = useState(42);
  const [rows, setRows] = useState<ExperimentRow[]>([]);
  const [history, setHistory] = useState<ExperimentSummary[]>([]);
  const [selectedId, setSelectedId] = useState<number | undefined>();
  const [busy, setBusy] = useState(false);
  const [historyBusy, setHistoryBusy] = useState(false);
  const [error, setError] = useState("");

  async function loadHistory() {
    setHistoryBusy(true);
    try {
      const response = await api.get("/api/experiments");
      setHistory(Array.isArray(response.data) ? response.data : []);
    } catch (err) {
      console.error("Unable to load experiment history:", err);
    } finally {
      setHistoryBusy(false);
    }
  }

  useEffect(() => { loadHistory(); }, []);

  async function run() {
    setBusy(true);
    setError("");
    setRows([]);
    setSelectedId(undefined);
    try {
      const experiment = (
        await api.post("/api/experiments", {
          name: `${type} comparison`,
          workload_type: type,
          duration_seconds: duration,
          seed,
        })
      ).data;
      const response = await api.post(`/api/experiments/${experiment.id}/start`);
      if (!Array.isArray(response.data) || response.data.length !== 2) {
        throw new Error("The experiment API did not return both systems.");
      }
      setRows(response.data);
      setSelectedId(experiment.id);
      await loadHistory();
    } catch (err) {
      console.error("Experiment comparison failed:", err);
      setError("Unable to run the comparison. Check the backend logs and try again.");
      await loadHistory();
    } finally {
      setBusy(false);
    }
  }

  async function viewExperiment(experiment: ExperimentSummary) {
    setError("");
    setType(experiment.workload_type);
    setSelectedId(experiment.id);
    setBusy(true);
    try {
      const response = await api.get(`/api/experiments/${experiment.id}/results`);
      setRows(Array.isArray(response.data) ? response.data : []);
      if (!Array.isArray(response.data) || response.data.length === 0) {
        setError(`Experiment #${experiment.id} has no saved results. Current status: ${experiment.status}.`);
      }
    } catch (err) {
      console.error(err);
      setError("Unable to load the selected experiment results.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <header className="page-head">
        <div>
          <div className="page-eyebrow">Evaluation lab</div>
          <h1 className="page-title">Controller Experiments</h1>
          <p className="page-description">
            Compare threshold-based management with the proposed agentic orchestrator using the same deterministic workload trace.
          </p>
        </div>
        <div className="page-actions">
          <span className="topbar-chip"><span className="chip-dot" /> DETERMINISTIC RUN</span>
        </div>
      </header>

      <section className="panel panel-pad" style={{ marginBottom: 16 }}>
        <div className="panel-header">
          <div>
            <h2 className="panel-title">Experiment configuration</h2>
            <p className="panel-subtitle">Choose a workload profile, simulation length and random seed. Identical settings keep comparisons reproducible.</p>
          </div>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <label htmlFor="workload-scenario" className="grid gap-2 text-xs font-semibold text-slate-600">
            Workload scenario
            <select id="workload-scenario" value={type} onChange={(event) => setType(event.target.value)} disabled={busy} className="min-w-40 rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-xs">
              {scenarios.map((scenario) => <option key={scenario} value={scenario}>{scenario}</option>)}
            </select>
          </label>
          <label htmlFor="experiment-duration" className="grid gap-2 text-xs font-semibold text-slate-600">
            Duration (steps)
            <input id="experiment-duration" type="number" min="10" max="3600" step="10" value={duration} onChange={event => setDuration(Number(event.target.value))} disabled={busy} className="w-28 px-3 py-2" />
          </label>
          <label htmlFor="experiment-seed" className="grid gap-2 text-xs font-semibold text-slate-600">
            Random seed
            <input id="experiment-seed" type="number" min="0" max="2147483647" value={seed} onChange={event => setSeed(Number(event.target.value))} disabled={busy} className="w-28 px-3 py-2" />
          </label>
          <button type="button" onClick={run} disabled={busy || !Number.isInteger(duration) || duration < 10 || duration > 3600 || !Number.isInteger(seed) || seed < 0} className="btn-primary">
            {busy ? "Running comparison…" : "Run comparison"}
          </button>
          <div className="ml-auto text-[10px] text-slate-500">1 step = 1 simulated minute</div>
        </div>
      </section>

      {error && <div role="alert" className="alert alert-error">{error}</div>}
      {busy && <div role="status" className="panel p-5 text-xs text-slate-500">Processing comparison or loading stored results…</div>}

      {rows.length === 2 && (
        <section className="panel panel-pad" style={{ marginBottom: 16 }}>
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Results: {type}</h2>
              <p className="panel-subtitle">Experiment #{selectedId ?? "—"} · {duration} simulated minutes · seed {seed}</p>
            </div>
            <span className="topbar-chip safety"><span className="chip-dot" /> 2 SYSTEMS COMPARED</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1250px]">
              <thead><tr className="border-b text-left">
                <th className="py-3 pr-4">System</th><th className="px-3 text-right">Avg CPU</th><th className="px-3 text-right">Avg Memory</th><th className="px-3 text-right">Latency (ms)</th><th className="px-3 text-right">Throughput</th><th className="px-3 text-right">Scaling</th><th className="px-3 text-right">Reaction (min)</th><th className="px-3 text-right">CPU Headroom</th><th className="px-3 text-right">SLO Violations</th><th className="px-3 text-right">Cost</th><th className="px-3 text-right">Energy</th><th className="px-3 text-right">CPU Forecast Score*</th><th className="px-3 text-right">Unnecessary Actions</th>
              </tr></thead>
              <tbody>{rows.map(row => (
                <tr key={row.system} className="border-b last:border-0">
                  <td className="py-3 pr-4 font-bold text-slate-800">{row.system}</td>
                  <td className="px-3 text-right">{number(row.avg_cpu)}%</td><td className="px-3 text-right">{number(row.avg_memory)}%</td><td className="px-3 text-right">{number(row.latency)}</td><td className="px-3 text-right">{number(row.throughput)}</td><td className="px-3 text-right">{row.scaling_actions}</td><td className="px-3 text-right">{number(row.reaction_time)}</td><td className="px-3 text-right">{number(row.resource_wastage)}%</td><td className="px-3 text-right">{row.slo_violations}</td><td className="px-3 text-right">{number(row.estimated_cost, 3)}</td><td className="px-3 text-right">{number(row.estimated_energy, 3)}</td><td className="px-3 text-right">{number(row.prediction_accuracy)}%</td><td className="px-3 text-right">{row.unnecessary_actions}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
          <p className="mt-4 border-t border-slate-100 pt-4 text-[10px] leading-5 text-slate-500">
            * CPU Forecast Score is the bounded 100 − CPU MAPE comparison score, not classification accuracy.
            CPU Headroom is 100 − average CPU utilization. Cost, energy and throughput are simulator proxies.
          </p>
        </section>
      )}

      {!busy && rows.length === 0 && !error && (
        <section className="panel p-8 text-center" style={{ marginBottom: 16 }}>
          <div className="mx-auto mb-3 grid h-11 w-11 place-items-center rounded-xl bg-indigo-50 text-lg font-bold text-indigo-600">↗</div>
          <h2 className="text-sm font-bold text-slate-700">No experiment results selected</h2>
          <p className="mx-auto mt-2 max-w-md text-xs leading-5 text-slate-500">Run a new comparison or select a completed experiment from your history below.</p>
        </section>
      )}

      <section className="panel overflow-hidden">
        <div className="panel-header px-5 pt-5">
          <div><h2 className="panel-title">Experiment history</h2><p className="panel-subtitle">Previously saved comparison runs are retained in the local database.</p></div>
          <button type="button" className="btn-secondary" onClick={loadHistory} disabled={historyBusy}>{historyBusy ? "Refreshing…" : "Refresh history"}</button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[650px]">
            <thead><tr className="border-b text-left"><th className="px-5 py-3">Run</th><th className="px-3 py-3">Scenario</th><th className="px-3 py-3">Duration</th><th className="px-3 py-3">Seed</th><th className="px-3 py-3">Status</th><th className="px-5 py-3 text-right">Results</th></tr></thead>
            <tbody>
              {history.map(item => (
                <tr key={item.id} className={"border-b last:border-0 " + (selectedId === item.id ? "bg-indigo-50/40" : "")}>
                  <td className="px-5 py-3 text-xs font-semibold text-slate-700">#{item.id}</td>
                  <td className="px-3 py-3 text-xs text-slate-600">{item.workload_type}</td>
                  <td className="px-3 py-3 text-xs text-slate-600">{item.duration_seconds} steps</td>
                  <td className="px-3 py-3 text-xs text-slate-600">{item.seed}</td>
                  <td className="px-3 py-3"><span className={"rounded-md px-2 py-1 text-[9px] font-bold " + (item.status === "COMPLETED" ? "bg-emerald-50 text-emerald-700" : item.status === "FAILED" ? "bg-rose-50 text-rose-700" : "bg-slate-100 text-slate-600")}>{item.status}</span></td>
                  <td className="px-5 py-3 text-right"><button type="button" className="btn-secondary min-h-8 px-3 py-1" disabled={item.status !== "COMPLETED"} onClick={() => viewExperiment(item)}>View</button></td>
                </tr>
              ))}
              {history.length === 0 && <tr><td colSpan={6} className="px-5 py-8 text-center text-slate-500">{historyBusy ? "Loading experiment history…" : "No saved experiments yet."}</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
