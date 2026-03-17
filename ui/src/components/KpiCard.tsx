import { type ReactNode } from "react";

type Tone = "warn" | "ok" | "bad" | "llm";

const toneClasses: Record<Tone, string> = {
  warn: "from-amber-500/15 to-amber-500/5 border-amber-500/20",
  ok: "from-emerald-500/15 to-emerald-500/5 border-emerald-500/20",
  bad: "from-rose-500/15 to-rose-500/5 border-rose-500/20",
  llm: "from-violet-500/15 to-violet-500/5 border-violet-500/20",
};

const iconBg: Record<Tone, string> = {
  warn: "bg-amber-500/20 text-amber-300",
  ok:   "bg-emerald-500/20 text-emerald-300",
  bad:  "bg-rose-500/20 text-rose-300",
  llm:  "bg-violet-500/20 text-violet-300",
};

interface KpiCardProps {
  title: string;
  value: number | string;
  tone: Tone;
  icon?: ReactNode;
}

export default function KpiCard({ title, value, tone, icon }: KpiCardProps) {
  return (
    <div className={`panel p-4 bg-gradient-to-br ${toneClasses[tone]}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="text-xs muted">{title}</div>
          <div className="mt-1 text-3xl font-semibold tracking-tight">{value}</div>
        </div>
        {icon && (
          <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${iconBg[tone]}`}>
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}

