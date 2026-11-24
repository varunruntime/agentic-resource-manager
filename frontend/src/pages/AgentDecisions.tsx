import { useEffect, useState } from "react";
import { api } from "../lib/api";

type Decision = {
  decision_id?: string; id?: number; timestamp?: string; action?: string; outcome?: string;
};
type DecisionDetail = Record<string, any>;

const stages = [
  ["Observation", "observation"],
  ["Analysis", "detected_problem"],
  ["Prediction", "prediction"],
  ["Reasoning", "reasoning"],
  ["Plan and alternatives", "plan"],
  ["Safety validation", "safety"],
  ["Execution", "execution"],
  ["Evaluation", "evaluation"],
];

function JsonPanel({ title, value }: { title: string; value: unknown }) {
  return (
    <section className="rounded-lg border border-slate-100 bg-slate-50/70 p-4">
      <h3 className="text-[10px] font-bold uppercase tracking-wider text-slate-500">{title}</h3>
      <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap break-words text-[10px] leading-5 text-slate-700">
        {value === undefined || value === null ? "Not recorded" : JSON.stringify(value, null, 2)}
      </pre>
    </section>
  );
}

export default function AgentDecisions() {
  const [rows, setRows] = useState<Decision[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<DecisionDetail | undefined>();
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");

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
    const interval = setInterval(loadDecisions, 10000);
    return () => clearInterval(interval);
  }, []);

  async function inspect(id?: string) {
    if (!id) return;
    setDetailLoading(true);
    setDetailError("");
    try {
      const response = await api.get(`/api/decisions/${encodeURIComponent(id)}`);
      setSelected(response.data);
    } catch (err) {
      console.error(err);
      setDetailError("Unable to retrieve the complete decision record.");
    } finally {
      setDetailLoading(false);
    }
  }

  return (
    <main>
      <header className="page-head">
        <div>
          <div className="page-eyebrow">Reasoning transparency</div>
          <h1 className="page-title">Agent Decisions</h1>
          <p className="page-description">
            Inspect the complete decision chain, candidate ranking, safety validation, simulated execution and post-action evaluation.
          </p>
        </div>
        <div className="page-actions">
          <button type="button" className="btn-secondary" onClick={loadDecisions}>Refresh records</button>
        </div>
      </header>

      <section className="panel overflow-hidden">
        <div className="panel-header px-5 pt-5">
          <div><h2 className="panel-title">Decision history</h2><p className="panel-subtitle">Select a record to inspect its complete agent reasoning chain.</p></div>
          <span className="topbar-chip safety"><span className="chip-dot" /> AUDIT VIEW</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[700px]">
            <thead><tr className="border-b text-left">
              <th className="px-5 py-3">Decision ID</th><th className="px-5 py-3">Timestamp</th><th className="px-5 py-3">Selected action</th><th className="px-5 py-3">Outcome</th><th className="px-5 py-3 text-right">Details</th>
            </tr></thead>
            <tbody>
              {loading && <tr><td colSpan={5} className="px-5 py-10 text-center text-slate-500">Loading decision records…</td></tr>}
              {!loading && error && <tr><td colSpan={5} className="px-5 py-10 text-center text-rose-600">{error}</td></tr>}
              {!loading && !error && rows.length === 0 && <tr><td colSpan={5} className="px-5 py-10 text-center text-slate-500">No agent decisions have been recorded yet. Run an agent cycle from the Dashboard.</td></tr>}
              {!loading && !error && rows.map((row, index) => (
                <tr key={row.decision_id ?? row.id ?? index} className="border-b last:border-0">
                  <td className="px-5 py-3 font-mono text-[10px] text-slate-500">{row.decision_id ?? row.id ?? "—"}</td>
                  <td className="px-5 py-3 text-xs text-slate-500">{row.timestamp ? new Date(row.timestamp).toLocaleString() : "—"}</td>
                  <td className="px-5 py-3"><span className="inline-flex rounded-md border border-indigo-100 bg-indigo-50 px-2.5 py-1 text-[10px] font-bold text-indigo-700">{row.action ?? "—"}</span></td>
                  <td className="px-5 py-3 text-xs font-semibold text-slate-600">{row.outcome ?? "—"}</td>
                  <td className="px-5 py-3 text-right"><button type="button" className="btn-secondary min-h-8 px-3 py-1" onClick={() => inspect(row.decision_id)}>Inspect</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {(detailLoading || detailError || selected) && (
        <section className="panel panel-pad mt-5">
          <div className="panel-header">
            <div><h2 className="panel-title">Decision detail</h2><p className="panel-subtitle">{selected?.decision_id || "Loading selected decision…"}</p></div>
            <button type="button" className="btn-secondary" onClick={() => setSelected(undefined)}>Close detail</button>
          </div>
          {detailLoading && <p role="status" className="text-xs text-slate-500">Loading full decision record…</p>}
          {detailError && <div role="alert" className="alert alert-error">{detailError}</div>}
          {selected && (
            <>
              <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
                <div className="rounded-lg border border-slate-100 p-3"><div className="text-[9px] font-bold uppercase text-slate-400">Selected action</div><div className="mt-1 text-sm font-bold text-slate-800">{selected.action}</div></div>
                <div className="rounded-lg border border-slate-100 p-3"><div className="text-[9px] font-bold uppercase text-slate-400">Outcome</div><div className="mt-1 text-sm font-bold text-slate-800">{selected.outcome}</div></div>
                <div className="rounded-lg border border-slate-100 p-3"><div className="text-[9px] font-bold uppercase text-slate-400">Safety</div><div className={"mt-1 text-sm font-bold " + (selected.safety?.approved ? "text-emerald-700" : "text-rose-700")}>{selected.safety?.approved ? "Approved" : "Rejected"}</div></div>
              </div>
              <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
                {stages.map(([title, key]) => <JsonPanel key={key} title={title} value={selected[key]} />)}
              </div>
              <div className="mt-3"><JsonPanel title="Feedback passed forward" value={selected.feedback || {
                selected_action: selected.action,
                outcome: selected.outcome,
                evaluation: selected.evaluation,
              }} /></div>
            </>
          )}
        </section>
      )}
    </main>
  );
}
