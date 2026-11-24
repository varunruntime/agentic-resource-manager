import { useEffect, useState } from "react";
import { api } from "../lib/api";
import Chart from "../components/Line";

type Prediction = {
  id: number;
  timestamp: string;
  horizon_minutes: number;
  cpu_predicted: number;
  memory_predicted: number;
  workload_predicted: number;
  confidence: number;
  mae: number;
  rmse: number;
  mape: number;
};

type Metric = { timestamp: string; cpu_percent: number; memory_percent: number };
function value(input: unknown, digits = 1) {
  if (input === null || input === undefined || input === "") return "—";
  const n = Number(input);
  return Number.isFinite(n) ? n.toFixed(digits) : "—";
}

export default function Predictions() {
  const [rows, setRows] = useState<Prediction[]>([]);
  const [actualRows, setActualRows] = useState<Metric[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    const [predictions, history] = await Promise.all([
      api.get("/api/predictions/history"),
      api.get("/api/resources/history"),
    ]);
    setRows(Array.isArray(predictions.data) ? predictions.data : []);
    setActualRows(Array.isArray(history.data) ? history.data : []);
  }

  useEffect(() => {
    load().catch((err) => {
      console.error(err);
      setError("Unable to load prediction history. Check the backend connection.");
    });
  }, []);

  async function run() {
    setBusy(true);
    setError("");
    try {
      const [current, history] = await Promise.all([
        api.get("/api/resources/current"),
        api.get("/api/resources/history"),
      ]);
      const observedHistory = history.data.length ? history.data : [current.data];
      await api.post("/api/agents/run", {
        history: observedHistory,
        state: current.data,
        mode: "recommendation",
      });
      await load();
    } catch (err) {
      console.error(err);
      setError("Prediction generation failed. Check the backend connection.");
    } finally {
      setBusy(false);
    }
  }

  const latest = rows.slice(-4);
  return (
    <main>
      <header className="page-head">
        <div>
          <div className="page-eyebrow">Forecast intelligence</div>
          <h1 className="page-title">Resource Predictions</h1>
          <p className="page-description">
            Review time-series resource forecasts, confidence and CPU validation metrics from chronological holdout evaluation.
          </p>
        </div>
        <div className="page-actions">
          <button type="button" disabled={busy} onClick={run} className="btn-primary">
            {busy ? "Generating…" : "Generate prediction"}
          </button>
        </div>
      </header>

      {error && <div role="alert" className="alert alert-error">{error}</div>}

      <section className="metrics-grid" style={{ gridTemplateColumns: "repeat(4,minmax(0,1fr))", marginBottom: 16 }}>
        {latest.map((prediction) => (
          <article className="metric-card" key={prediction.id}>
            <div className="metric-top">
              <span className="metric-label">{prediction.horizon_minutes}-minute CPU forecast</span>
              <span className="metric-symbol">CPU</span>
            </div>
            <div className="metric-value-row">
              <span className="metric-value">{value(prediction.cpu_predicted)}</span>
              <span className="metric-unit">%</span>
            </div>
            <div className="metric-detail">
              {Number(prediction.confidence) > 0
                ? `Validation confidence ${value(prediction.confidence, 2)}`
                : "Validation not available yet"}
            </div>
          </article>
        ))}
        {latest.length === 0 && (
          <div className="panel p-5 text-xs text-slate-500" style={{ gridColumn: "1 / -1" }}>
            No forecasts available yet. Generate a prediction after resource readings have been collected.
          </div>
        )}
      </section>

      <section className="panel panel-pad" style={{ marginBottom: 16 }}>
        <div className="panel-header">
          <div>
            <h2 className="panel-title">Observed resource history</h2>
            <p className="panel-subtitle">Actual CPU and memory measurements. Forecasts are listed separately below.</p>
          </div>
          <div className="chart-legend">
            <span className="legend-item"><span className="legend-swatch" /> CPU</span>
            <span className="legend-item"><span className="legend-swatch teal" /> Memory</span>
          </div>
        </div>
        <Chart data={actualRows} keys={["cpu_percent", "memory_percent"]} />
      </section>

      <section className="panel panel-pad">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">Forecast validation</h2>
            <p className="panel-subtitle">MAE, RMSE and MAPE use chronological CPU holdout predictions.</p>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[780px]">
            <thead>
              <tr className="border-b text-left">
                <th className="py-3">Horizon</th>
                <th>CPU forecast</th>
                <th>Memory forecast</th>
                <th>Workload forecast</th>
                <th>Confidence</th>
                <th>CPU MAE</th>
                <th>CPU RMSE</th>
                <th>CPU MAPE</th>
              </tr>
            </thead>
            <tbody>
              {latest.map((prediction) => (
                <tr key={prediction.id} className="border-b last:border-0">
                  <td className="py-3 font-semibold text-slate-700">{prediction.horizon_minutes} min</td>
                  <td>{value(prediction.cpu_predicted)}%</td>
                  <td>{value(prediction.memory_predicted)}%</td>
                  <td>{value(prediction.workload_predicted)}</td>
                  <td>{value(prediction.confidence, 2)}</td>
                  <td>{prediction.confidence > 0 ? value(prediction.mae, 3) : "N/A"}</td>
                  <td>{prediction.confidence > 0 ? value(prediction.rmse, 3) : "N/A"}</td>
                  <td>{prediction.confidence > 0 ? value(prediction.mape, 2) + "%" : "N/A"}</td>
                </tr>
              ))}
              {latest.length === 0 && (
                <tr><td colSpan={8} className="py-8 text-center text-slate-500">No prediction records yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
        <p className="mt-4 border-t border-slate-100 pt-4 text-[10px] leading-5 text-slate-500">
          Validation metrics remain unavailable until sufficient observed history exists. Confidence is not a guarantee of forecast correctness.
        </p>
      </section>
    </main>
  );
}
