import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type ChartProps = {
  data: Record<string, any>[];
  keys: string[];
};

export default function Chart({ data, keys }: ChartProps) {
  if (!data.length) {
    return (
      <div className="chart-wrap" style={{ display: "grid", placeItems: "center" }}>
        <div style={{ textAlign: "center", color: "#8995a7", fontSize: 11 }}>
          <div style={{ fontWeight: 700, color: "#526078", marginBottom: 5 }}>No telemetry recorded yet</div>
          Resource readings will appear here when the simulator starts.
        </div>
      </div>
    );
  }

  return (
    <div className="chart-wrap">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 10, right: 12, left: -18, bottom: 2 }}>
          <CartesianGrid stroke="#edf1f6" strokeDasharray="3 4" vertical={false} />
          <XAxis dataKey="timestamp" hide />
          <YAxis
            tick={{ fill: "#8995a7", fontSize: 9 }}
            axisLine={false}
            tickLine={false}
            width={38}
          />
          <Tooltip
            contentStyle={{
              border: "1px solid #e4eaf1",
              borderRadius: 9,
              boxShadow: "0 8px 24px rgba(23, 36, 58, .10)",
              fontSize: 10,
            }}
            labelStyle={{ color: "#526078", fontWeight: 700, marginBottom: 4 }}
          />
          {keys[0] && (
            <Line
              type="monotone"
              dataKey={keys[0]}
              name={keys[0].replace(/_/g, " ")}
              stroke="#4267d5"
              strokeWidth={2.4}
              dot={false}
              activeDot={{ r: 4, strokeWidth: 0 }}
              connectNulls
            />
          )}
          {keys[1] && (
            <Line
              type="monotone"
              dataKey={keys[1]}
              name={keys[1].replace(/_/g, " ")}
              stroke="#0f9f8f"
              strokeWidth={2.4}
              dot={false}
              activeDot={{ r: 4, strokeWidth: 0 }}
              connectNulls
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
