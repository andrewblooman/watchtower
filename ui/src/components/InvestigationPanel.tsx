import type { ReasoningTurn, SessionDetail } from "@/lib/types";
import { formatTs } from "@/lib/time";

interface InvestigationPanelProps {
  detail: SessionDetail | null;
  reasoning: ReasoningTurn[];
}

export default function InvestigationPanel({ detail, reasoning }: InvestigationPanelProps) {
  const summary = detail?.summary;
  const latestReasoning = reasoning[reasoning.length - 1];

  return (
    <div className="space-y-3">
      {detail && (
        <div className="text-xs muted">
          {detail.session.github_repo} @{" "}
          <span className="font-mono">{detail.session.commit_short}</span>
        </div>
      )}

      <div className="text-sm text-slate-200">
        <div className="text-xs muted">AI Diagnosis</div>
        <div className="mt-1 leading-relaxed">
          {summary?.root_cause ?? latestReasoning?.response?.slice(0, 200) ?? "Investigating"}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-lg border border-white/10 bg-white/5 p-3">
          <div className="text-xs muted">Confidence</div>
          <div className="mt-1 text-lg font-semibold">
            {summary?.confidence != null
              ? `${Math.round(summary.confidence * 100)}%`
              : ""}
          </div>
        </div>
        <div className="rounded-lg border border-white/10 bg-white/5 p-3">
          <div className="text-xs muted">Resolution</div>
          <div className="mt-1 text-sm capitalize">
            {summary?.resolution ?? "Pending"}
          </div>
        </div>
      </div>

      {summary?.recommendation && (
        <div className="rounded-lg border border-indigo-500/20 bg-indigo-500/10 p-3">
          <div className="text-xs muted mb-1">Recommendation</div>
          <div className="text-sm text-slate-200">{summary.recommendation}</div>
        </div>
      )}

      <div className="rounded-lg border border-white/10 bg-white/5 p-3">
        <div className="text-xs muted mb-2">Reasoning History</div>
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {reasoning.map((r) => (
            <div key={r.turn} className="flex items-start gap-2 text-xs">
              <span className="shrink-0 rounded bg-violet-500/20 px-1.5 py-0.5 text-violet-300 font-mono">
                T{r.turn}
              </span>
              <div className="min-w-0">
                <div className="text-slate-300 truncate">{r.prompt_summary}</div>
                <div className="muted">{formatTs(r.ts)}</div>
              </div>
            </div>
          ))}
          {reasoning.length === 0 && (
            <div className="text-xs muted">
              {detail ? "Awaiting first reasoning turn" : "Select a session to view details."}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
