import { useState } from "react";
import { api } from "../lib/api";

type Weights = { performance: number; cost: number; energy: number; utilization: number };
export default function Optimization() {
  const [weights, setWeights] = useState<Weights>({ performance: .4, cost: .25, energy: .2, utilization: .15 });
  const [result, setResult] = useState<any>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const total = Object.values(weights).reduce((sum, value) => sum + value, 0);

  function change(key: keyof Weights, percent: number) {
    setWeights(previous => ({ ...previous, [key]: percent / 100 }));
  }
  async function run() {
    if (Math.abs(total - 1) > .001) return;
    setBusy(true); setError("");
    try {
      const response = await api.post("/api/agents/run?mode=recommendation", weights);
      setResult(response.data);
    } catch (err) {
      console.error(err);
      setError("Unable to score candidate actions. Check the backend logs.");
    } finally { setBusy(false); }
  }

  return (
    <main>
      <header className="page-head">
        <div>
          <div className="page-eyebrow">Decision optimization</div>
          <h1 className="page-title">Multi-Objective Optimization</h1>
          <p className="page-description">Adjust the relative importance of performance, operating cost, energy and utilization objectives.</p>
        </div>
      </header>
      {error && <div role="alert" className="alert alert-error">{error}</div>}
      <section className="panel panel-pad" style={{ maxWidth: 820 }}>
        <div className="panel-header">
          <div><h2 className="panel-title">Objective weights</h2><p className="panel-subtitle">The weights must add up to 100% before scoring candidate actions.</p></div>
          <span className="topbar-chip">WEIGHTED SCORING</span>
        </div>
        <div className="grid gap-6">
          {(["performance", "cost", "energy", "utilization"] as const).map(key => (
            <label key={key} className="block">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-xs font-bold capitalize text-slate-700">{key}</span>
                <span className="text-xs font-bold tabular-nums text-slate-600">{Math.round(weights[key] * 100)}%</span>
              </div>
              <input className="w-full accent-indigo-600" type="range" min="0" max="100" value={Math.round(weights[key] * 100)} onChange={event => change(key, Number(event.target.value))} />
            </label>
          ))}
        </div>
        <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-5">
          <div className={"text-xs font-bold " + (Math.abs(total - 1) < .001 ? "text-emerald-700" : "text-rose-600")}>
            Total weight: {Math.round(total * 100)}% {Math.abs(total - 1) >= .001 && "— adjust to 100%"}
          </div>
          <button type="button" disabled={busy || Math.abs(total - 1) >= .001} onClick={run} className="btn-primary">
            {busy ? "Scoring actions…" : "Score candidate actions"}
          </button>
        </div>
      </section>

      {result && (
        <section className="panel panel-pad mt-5" style={{ maxWidth: 820 }}>
          <div className="panel-header">
            <div><h2 className="panel-title">Candidate action scores</h2><p className="panel-subtitle">Scores returned by the active reasoning and optimization pipeline.</p></div>
          </div>
          <div className="grid gap-3">
            {(result.candidate_actions || []).map((action: any) => (
              <div key={action.action} className="flex items-center justify-between gap-4 rounded-lg border border-slate-100 bg-slate-50/70 p-4">
                <div><div className="text-xs font-bold text-slate-800">{action.action}</div><p className="mt-1 text-[10px] leading-5 text-slate-500">{action.reason}</p></div>
                <div className="text-lg font-bold tabular-nums text-indigo-700">{Number(action.score).toFixed(3)}</div>
              </div>
            ))}
            {(!result.candidate_actions || result.candidate_actions.length === 0) && <p className="text-xs text-slate-500">No candidate actions were returned for the current state.</p>}
          </div>
        </section>
      )}
    </main>
  );
}
