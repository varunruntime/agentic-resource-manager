import { useEffect, useState } from "react";
import { api } from "../lib/api";

type Decision = {
  decision_id?: string;
  id?: number;
  timestamp?: string;
  action?: string;
  outcome?: string;
};

export default function AgentDecisions() {
  const [rows, setRows] = useState<Decision[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadDecisions = async () => {
    try {
      const response = await api.get("/api/decisions");
      setRows(Array.isArray(response.data) ? response.data : []);
      setError("");
    } catch (err) {
      console.error(err);
      setError("Failed to load agent decisions. Check the backend connection.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDecisions();
    const interval = setInterval(loadDecisions, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <main>
      <header className="page-head">
        <div>
          <div className="page-eyebrow">Reasoning transparency</div>
          <h1 className="page-title">Agent Decisions</h1>
          <p className="page-description">
            Inspect the actions produced by the resource management agent and their recorded outcomes.
          </p>
        </div>
        <div className="page-actions">
          <button type="button" className="btn-secondary" onClick={loadDecisions}>Refresh records</button>
        </div>
      </header>

      <section className="panel overflow-hidden">
        <div className="panel-header px-5 pt-5">
          <div>
            <h2 className="panel-title">Decision history</h2>
            <p className="panel-subtitle">Automatically refreshes every five seconds.</p>
          </div>
          <span className="topbar-chip safety"><span className="chip-dot" /> AUDIT VIEW</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px]">
            <thead>
              <tr className="border-b text-left">
                <th className="px-5 py-3">Decision ID</th>
                <th className="px-5 py-3">Timestamp</th>
                <th className="px-5 py-3">Selected action</th>
                <th className="px-5 py-3">Outcome</th>
              </tr>
            </thead>
            <tbody>
              {loading && <tr><td colSpan={4} className="px-5 py-10 text-center text-slate-500">Loading decision records…</td></tr>}
              {!loading && error && <tr><td colSpan={4} className="px-5 py-10 text-center text-rose-600">{error}</td></tr>}
              {!loading && !error && rows.length === 0 && <tr><td colSpan={4} className="px-5 py-10 text-center text-slate-500">No agent decisions have been recorded yet.</td></tr>}
              {!loading && !error && rows.map((row, index) => (
                <tr key={row.decision_id ?? row.id ?? index} className="border-b last:border-0">
                  <td className="px-5 py-3 font-mono text-[10px] text-slate-500">{row.decision_id ?? row.id ?? "—"}</td>
                  <td className="px-5 py-3 text-xs text-slate-500">{row.timestamp ? new Date(row.timestamp).toLocaleString() : "—"}</td>
                  <td className="px-5 py-3"><span className="inline-flex rounded-md border border-indigo-100 bg-indigo-50 px-2.5 py-1 text-[10px] font-bold text-indigo-700">{row.action ?? "—"}</span></td>
                  <td className="px-5 py-3 text-xs font-semibold text-slate-600">{row.outcome ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
