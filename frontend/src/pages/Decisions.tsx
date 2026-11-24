import { useEffect, useState } from "react";
import { api } from "../lib/api";

type DecisionRow = {
  decision_id?: string;
  timestamp?: string;
  action?: string;
  outcome?: string;
};

export default function Decisions() {
  const [rows, setRows] = useState<DecisionRow[]>([]);
  const [error, setError] = useState("");

  async function load() {
    try {
      const response = await api.get("/api/decisions");
      setRows(Array.isArray(response.data) ? response.data : []);
      setError("");
    } catch (err) {
      console.error(err);
      setError("Unable to load decision logs. Check the backend connection.");
    }
  }

  useEffect(() => { load(); }, []);

  const exportUrl = (import.meta.env.VITE_API_URL || "http://localhost:8000") + "/api/decisions/export.csv";

  return (
    <main>
      <header className="page-head">
        <div>
          <div className="page-eyebrow">Audit trail</div>
          <h1 className="page-title">Decision Logs</h1>
          <p className="page-description">Review recorded agent actions and export the decision history for further analysis.</p>
        </div>
        <div className="page-actions">
          <button type="button" className="btn-secondary" onClick={load}>Refresh</button>
          <a className="btn-primary no-underline" href={exportUrl}>Export CSV ↗</a>
        </div>
      </header>
      {error && <div role="alert" className="alert alert-error">{error}</div>}
      <section className="panel overflow-hidden">
        <div className="panel-header px-5 pt-5">
          <div>
            <h2 className="panel-title">Recorded decisions</h2>
            <p className="panel-subtitle">{rows.length} records available in the current history.</p>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[620px]">
            <thead><tr className="border-b text-left"><th className="px-5 py-3">Decision ID</th><th className="px-5 py-3">Timestamp</th><th className="px-5 py-3">Action</th><th className="px-5 py-3">Outcome</th></tr></thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={row.decision_id ?? index} className="border-b last:border-0">
                  <td className="px-5 py-3 font-mono text-[10px] text-slate-500">{row.decision_id ?? "—"}</td>
                  <td className="px-5 py-3 text-xs text-slate-500">{row.timestamp ? new Date(row.timestamp).toLocaleString() : "—"}</td>
                  <td className="px-5 py-3 text-xs font-semibold text-slate-700">{row.action ?? "—"}</td>
                  <td className="px-5 py-3 text-xs text-slate-600">{row.outcome ?? "—"}</td>
                </tr>
              ))}
              {!error && rows.length === 0 && <tr><td colSpan={4} className="px-5 py-10 text-center text-slate-500">No decision records available yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
