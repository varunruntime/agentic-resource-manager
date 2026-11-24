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

      const data = Array.isArray(response.data)
        ? response.data
        : [];

      setRows(data);
      setError("");
    } catch (err) {
      console.error(err);
      setError("Failed to load agent decisions.");
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
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">
          Agent Decisions
        </h1>

        <p className="mt-1 text-slate-500">
          Transparent decision-chain inspection.
        </p>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="px-6 py-4 text-left text-sm font-semibold text-slate-600">
                  Decision ID
                </th>

                <th className="px-6 py-4 text-left text-sm font-semibold text-slate-600">
                  Time
                </th>

                <th className="px-6 py-4 text-left text-sm font-semibold text-slate-600">
                  Action
                </th>

                <th className="px-6 py-4 text-left text-sm font-semibold text-slate-600">
                  Outcome
                </th>
              </tr>
            </thead>

            <tbody>
              {loading && (
                <tr>
                  <td
                    colSpan={4}
                    className="px-6 py-10 text-center text-slate-500"
                  >
                    Loading decisions...
                  </td>
                </tr>
              )}

              {!loading && error && (
                <tr>
                  <td
                    colSpan={4}
                    className="px-6 py-10 text-center text-red-500"
                  >
                    {error}
                  </td>
                </tr>
              )}

              {!loading && !error && rows.length === 0 && (
                <tr>
                  <td
                    colSpan={4}
                    className="px-6 py-10 text-center text-slate-500"
                  >
                    No agent decisions yet.
                  </td>
                </tr>
              )}

              {!loading &&
                !error &&
                rows.map((row, index) => (
                  <tr
                    key={row.decision_id ?? row.id ?? index}
                    className="border-b border-slate-100 last:border-0"
                  >
                    <td className="px-6 py-4 font-mono text-xs text-slate-600">
                      {row.decision_id ?? row.id ?? "—"}
                    </td>

                    <td className="px-6 py-4 text-sm text-slate-600">
                      {row.timestamp
                        ? new Date(row.timestamp).toLocaleString()
                        : "—"}
                    </td>

                    <td className="px-6 py-4">
                      <span className="rounded-full bg-indigo-50 px-3 py-1 text-sm font-medium text-indigo-700">
                        {row.action ?? "—"}
                      </span>
                    </td>

                    <td className="px-6 py-4 text-sm font-medium text-slate-700">
                      {row.outcome ?? "—"}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}