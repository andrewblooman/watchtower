import type { IdName } from "@/lib/types";

interface FilterSelectProps {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: IdName[];
}

export default function FilterSelect({ label, value, onChange, options }: FilterSelectProps) {
  return (
    <label className="flex flex-col gap-1 text-xs">
      <span className="muted">{label}</span>
      <select
        className="h-10 rounded-lg border border-white/10 bg-slate-950/60 px-3 text-sm text-slate-100 outline-none focus:border-indigo-400/60"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {options.map((o) => (
          <option key={o.id} value={o.id}>
            {o.name}
          </option>
        ))}
      </select>
    </label>
  );
}
