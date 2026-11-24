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

type Metric = {
  timestamp: string;
  cpu_percent: number;
  memory_percent: number;
};

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
    setRows(predictions.data);
    setActualRows(history.data);
  }

  useEffect(() => {
    load().catch((err) => {
      console.error(err);
      setError("Unable to load prediction history.");
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
      const observedHistory = history.data.length
        ? history.data
        : [current.data];

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
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold">Predictions</h1>
          <p className="mt-1 text-slate-500">
            Time-series forecasts with measured error metrics.
          </p>
        </div>
        <button
          disabled={busy}
          onClick={run}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-white disabled:opacity-50"
        >
          {busy ? "Generating..." : "Generate Prediction"}
        </button>
      </div>

      {error && (
        <div role="alert" className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <section className="mb-6 grid grid-cols-4 gap-4">
        {latest.map((prediction) => (
          <div key={prediction.id} className="rounded-xl border bg-white p-4">
            <div className="text-sm text-slate-500">
              {prediction.horizon_minutes} min forecast
            </div>
            <div className="mt-1 text-2xl font-bold">
              {Number(prediction.cpu_predicted).toFixed(1)}%
            </div>
            <div className="mt-1 text-xs text-slate-500">
              {Number(prediction.confidence) > 0
                ? `Confidence ${Number(prediction.confidence).toFixed(2)}`
                : "Validation not available yet"}
            </div>
          </div>
        ))}
      </section>

      <section className="rounded-xl border bg-white p-5">
        <h2 className="mb-3 font-semibold">Actual Historical CPU & Memory</h2>
        <Chart data={actualRows} keys={["cpu_percent", "memory_percent"]} />
      </section>

      <section className="mt-5 rounded-xl border bg-white p-5">
        <h2 className="mb-1 font-semibold">CPU Forecast Quality</h2>
        <p className="mb-4 text-xs text-slate-500">
          MAE, RMSE and MAPE are calculated from chronological CPU holdout
          predictions. Metrics are unavailable until at least four readings exist.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b text-left text-slate-500">
                <th className="py-2">Horizon</th>
                <th>CPU</th>
                <th>Memory</th>
                <th>Workload</th>
                <th>Confidence</th>
                <th>CPU MAE</th>
                <th>CPU RMSE</th>
                <th>CPU MAPE</th>
              </tr>
            </thead>
            <tbody>
              {latest.map((prediction) => (
                <tr key={prediction.id} className="border-b">
                  <td className="py-2">{prediction.horizon_minutes} min</td>
                  <td>{Number(prediction.cpu_predicted).toFixed(1)}%</td>
                  <td>{Number(prediction.memory_predicted).toFixed(1)}%</td>
                  <td>{Number(prediction.workload_predicted).toFixed(1)}</td>
                  <td>{Number(prediction.confidence).toFixed(2)}</td>
                  <td>{prediction.confidence > 0 ? Number(prediction.mae).toFixed(3) : "N/A"}</td>
                  <td>{prediction.confidence > 0 ? Number(prediction.rmse).toFixed(3) : "N/A"}</td>
                  <td>{prediction.confidence > 0 ? `${Number(prediction.mape).toFixed(2)}%` : "N/A"}</td>
                </tr>
              ))}
              {latest.length === 0 && (
                <tr>
                  <td colSpan={8} className="py-6 text-center text-slate-500">
                    No predictions recorded yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
