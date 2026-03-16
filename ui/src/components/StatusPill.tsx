type StatusVariant = "rollback_in_progress" | "investigating" | "analyzing" | "resolved" | string;

const variantMap: Record<string, string> = {
  rollback_in_progress: "bg-rose-500/20 text-rose-200 border-rose-400/30",
  investigating: "bg-emerald-500/20 text-emerald-200 border-emerald-400/30",
  analyzing: "bg-sky-500/20 text-sky-200 border-sky-400/30",
  resolved: "bg-slate-500/20 text-slate-300 border-slate-400/30",
};

function classes(status: StatusVariant): string {
  return variantMap[status] ?? "bg-white/5 text-slate-300 border-white/10";
}

interface StatusPillProps {
  status: StatusVariant;
}

export default function StatusPill({ status }: StatusPillProps) {
  const label = status.replaceAll("_", " ");
  return (
    <span
      className={`inline-flex items-center rounded-md border px-2 py-1 text-xs font-medium capitalize ${classes(status)}`}
    >
      {label}
    </span>
  );
}
