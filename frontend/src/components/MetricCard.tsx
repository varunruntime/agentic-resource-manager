type MetricCardProps = {
  label: string;
  value: string | number;
  unit?: string;
};

export default function MetricCard({
  label,
  value,
  unit = "",
}: MetricCardProps) {
  return (
    <div className="bg-white rounded-xl p-4 shadow-sm border">
      <div className="text-sm text-slate-500">
        {label}
      </div>

      <div className="text-2xl font-bold mt-1">
        {value}

        <span className="text-sm font-normal ml-1">
          {unit}
        </span>
      </div>
    </div>
  );
}