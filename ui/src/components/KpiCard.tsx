type Tone = "warn" | "ok" | "bad" | "llm";

const toneClasses: Record<Tone, string> = {
  warn: "from-amber-500/15 to-amber-500/5 border-amber-500/20",
  ok: "from-emerald-500/15 to-emerald-500/5 border-emerald-500/20",
  bad: "from-rose-500/15 to-rose-500/5 border-rose-500/20",
  llm: "from-violet-500/15 to-violet-500/5 border-violet-500/20",
};

interface KpiCardProps {
  title: string;
  value: number;
  tone: Tone;
}

export default function KpiCard({ title, value, tone }: KpiCardProps) {
  return (
    <div className={`panel p-4 bg-gradient-to-br ${toneClasses[tone]}`}>
      <div className="text-xs muted">{title}</div>
      <div className="mt-1 text-3xl font-semibold tracking-tight">{value}</div>
    </div>
  );
}
