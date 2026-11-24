import { useEffect, useState } from "react";
import { api } from "../lib/api";

type AgentStatus = { llm_available?: boolean; llm_configured?: boolean; [key: string]: unknown };
export default function Settings() {
  const [status, setStatus] = useState<AgentStatus | undefined>();
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/api/agents/status")
      .then(response => setStatus(response.data))
      .catch(err => { console.error(err); setError("Unable to retrieve agent status from the backend."); });
  }, []);

  const items = [
    { label: "Execution environment", value: "Simulation only", detail: "No live cloud resources are modified." },
    { label: "Safety policy", value: "Enabled", detail: "Predefined actions are checked before simulated execution." },
    { label: "Orchestrator", value: "Nine-stage closed loop", detail: "Observe through feedback, with safety validation before action." },
    { label: "Active reasoning provider", value: "Rule-based", detail: "Deterministic reasoning is the configured default provider." },
    { label: "External LLM integration", value: status?.llm_configured ? "API key configured · not invoked" : "Not configured · not invoked", detail: "The current build does not make a live OpenAI/Gemini API call; reasoning remains rule-based." },
  ];

  return (
    <main>
      <header className="page-head">
        <div>
          <div className="page-eyebrow">Platform configuration</div>
          <h1 className="page-title">System Settings</h1>
          <p className="page-description">Review the execution boundary, safety configuration and currently active reasoning mode.</p>
        </div>
        <div className="page-actions"><span className="topbar-chip safety"><span className="chip-dot" /> SAFE DEFAULTS</span></div>
      </header>
      {error && <div role="alert" className="alert alert-error">{error}</div>}
      <section className="panel panel-pad">
        <div className="panel-header">
          <div><h2 className="panel-title">Runtime configuration</h2><p className="panel-subtitle">Read-only status for this demonstration environment.</p></div>
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {items.map(item => (
            <article key={item.label} className="rounded-lg border border-slate-100 bg-slate-50/70 p-4">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{item.label}</div>
              <div className="mt-2 text-sm font-bold text-slate-800">{item.value}</div>
              <p className="mt-1 text-[10px] leading-5 text-slate-500">{item.detail}</p>
            </article>
          ))}
        </div>
        <div className="mt-5 border-t border-slate-100 pt-4 text-[10px] leading-5 text-slate-500">
          Agent status endpoint: {status ? "Connected" : "Waiting for status"}.
          {" The active provider is rule-based; API-key presence does not activate an external LLM call."}
        </div>
      </section>
    </main>
  );
}
