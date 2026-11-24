type MetricCardProps = {
  label: string;
  value: string | number;
  unit?: string;
  symbol?: string;
  detail?: string;
};

export default function MetricCard({
  label,
  value,
  unit = "",
  symbol = "MET",
  detail = "Latest observed value",
}: MetricCardProps) {
  return (
    <article className="metric-card">
      <div className="metric-top">
        <span className="metric-label">{label}</span>
        <span className="metric-symbol" aria-hidden="true">{symbol}</span>
      </div>
      <div className="metric-value-row">
        <span className="metric-value">{value}</span>
        {unit && <span className="metric-unit">{unit}</span>}
      </div>
      <div className="metric-detail">{detail}</div>
    </article>
  );
}
