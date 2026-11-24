import { useEffect, useState } from "react";
import { api } from "../lib/api";

type Workload = {
  id: number; name: string; workload_type: string; initial_load: number;
  growth_rate: number; duration_seconds: number; current_load: number; active: boolean;
};
const patterns = ["Stable", "Increasing", "Decreasing", "Sudden Spike", "Periodic", "Random", "Anomaly"];

export default function Workloads() {
  const [rows, setRows] = useState<Workload[]>([]);
  const [form, setForm] = useState({
    name: "Sudden Spike Demo", workload_type: "Sudden Spike",
    initial_load: 35, growth_rate: 1, duration_seconds: 60,
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function load() {
    try {
      const response = await api.get("/api/workloads");
      setRows(Array.isArray(response.data) ? response.data : []);
      setError("");
    } catch (err) {
      console.error(err);
      setError("Unable to load workloads. Check the backend connection.");
    }
  }

  useEffect(() => {
    load();
    const interval = setInterval(load, 2500);
    return () => clearInterval(interval);
  }, []);

  async function create() {
    setBusy(true); setMessage(""); setError("");
    try {
      await api.post("/api/workloads", form);
      setMessage("Workload created successfully.");
      await load();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Unable to create workload.");
    } finally { setBusy(false); }
  }

  async function toggle(workload: Workload) {
    setError(""); setMessage("");
    try {
      await api.post(`/api/workloads/${workload.id}/${workload.active ? "stop" : "start"}`);
      setMessage(workload.active ? "Workload stopped." : "Workload started.");
      await load();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Unable to update workload status.");
    }
  }

  return (
    <main>
      <header className="page-head">
        <div>
          <div className="page-eyebrow">Workload orchestration</div>
          <h1 className="page-title">Workload Management</h1>
          <p className="page-description">Create and control reproducible load patterns for resource monitoring and experiment runs.</p>
        </div>
        <div className="page-actions"><button type="button" onClick={load} className="btn-secondary">Refresh library</button></div>
      </header>

      {error && <div role="alert" className="alert alert-error">{error}</div>}
      {message && <div role="status" className="alert" style={{ borderColor: "#cfe9e2", background: "#f2fbf8", color: "#147b68" }}>{message}</div>}

      <section className="panel panel-pad" style={{ marginBottom: 16 }}>
        <div className="panel-header">
          <div><h2 className="panel-title">Create workload profile</h2><p className="panel-subtitle">Define the initial load and how it changes over the simulation.</p></div>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5">
          <label className="grid gap-2 text-[10px] font-bold text-slate-600">Workload name
            <input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="Workload name" className="px-3 py-2" />
          </label>
          <label className="grid gap-2 text-[10px] font-bold text-slate-600">Pattern
            <select value={form.workload_type} onChange={e => setForm({ ...form, workload_type: e.target.value })} className="px-3 py-2">
              {patterns.map(pattern => <option key={pattern}>{pattern}</option>)}
            </select>
          </label>
          <label className="grid gap-2 text-[10px] font-bold text-slate-600">Initial load (%)
            <input type="number" min="0" max="100" value={form.initial_load} onChange={e => setForm({ ...form, initial_load: Number(e.target.value) })} className="px-3 py-2" />
          </label>
          <label className="grid gap-2 text-[10px] font-bold text-slate-600">Growth rate
            <input type="number" min="-100" max="100" value={form.growth_rate} onChange={e => setForm({ ...form, growth_rate: Number(e.target.value) })} className="px-3 py-2" />
          </label>
          <label className="grid gap-2 text-[10px] font-bold text-slate-600">Duration (seconds)
            <input type="number" min="1" value={form.duration_seconds} onChange={e => setForm({ ...form, duration_seconds: Number(e.target.value) })} className="px-3 py-2" />
          </label>
        </div>
        <div className="mt-4 flex items-center gap-3">
          <button type="button" disabled={busy || !form.name.trim() || form.initial_load < 0 || form.initial_load > 100 || form.duration_seconds < 1 || form.growth_rate < -100 || form.growth_rate > 100} onClick={create} className="btn-primary">
            {busy ? "Creating…" : "Create workload"}
          </button>
          <span className="text-[10px] text-slate-400">Runs in the local simulation environment.</span>
        </div>
      </section>

      <section className="panel overflow-hidden">
        <div className="panel-header px-5 pt-5">
          <div><h2 className="panel-title">Workload library</h2><p className="panel-subtitle">{rows.length} configured workload profiles</p></div>
          <span className="topbar-chip"><span className="chip-dot" /> SIMULATOR</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px]">
            <thead><tr className="border-b text-left">
              <th className="px-5 py-3">Name</th><th className="px-3 py-3">Pattern</th><th className="px-3 py-3">Initial load</th><th className="px-3 py-3">Current load</th><th className="px-3 py-3">Growth</th><th className="px-3 py-3">Duration</th><th className="px-3 py-3">Status</th><th className="px-5 py-3 text-right">Action</th>
            </tr></thead>
            <tbody>
              {rows.map(workload => (
                <tr key={workload.id} className="border-b last:border-0">
                  <td className="px-5 py-3 font-semibold text-slate-700">{workload.name}</td>
                  <td className="px-3 py-3">{workload.workload_type}</td>
                  <td className="px-3 py-3">{workload.initial_load}%</td>
                  <td className="px-3 py-3"><div className="flex min-w-24 items-center gap-2"><div className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-indigo-500" style={{ width: Math.max(0, Math.min(100, workload.current_load || 0)) + "%" }} /></div><span className="text-[10px] tabular-nums">{Number(workload.current_load || 0).toFixed(0)}%</span></div></td>
                  <td className="px-3 py-3">{workload.growth_rate}</td>
                  <td className="px-3 py-3">{workload.duration_seconds}s</td>
                  <td className="px-3 py-3"><span className={"inline-flex rounded-md px-2 py-1 text-[9px] font-bold " + (workload.active ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500")}>{workload.active ? "RUNNING" : "STOPPED"}</span></td>
                  <td className="px-5 py-3 text-right"><button type="button" onClick={() => toggle(workload)} className="btn-secondary min-h-8 px-3 py-1">{workload.active ? "Stop" : "Start"}</button></td>
                </tr>
              ))}
              {rows.length === 0 && !error && <tr><td colSpan={8} className="px-5 py-10 text-center text-slate-500">No workload profiles available. Create one above to get started.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
