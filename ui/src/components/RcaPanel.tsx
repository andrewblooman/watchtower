import type { EventRow, IncidentDetail } from "@/lib/types";
import { formatTs } from "@/lib/time";

interface RcaPanelProps {
  detail: IncidentDetail | null;
  events: EventRow[];
  serviceName: string;
  envName: string;
  onViewAllTimeline?: () => void;
}

export default function RcaPanel({ detail, events, serviceName, envName, onViewAllTimeline }: RcaPanelProps) {
  return (
    <div className="space-y-3">
      <div className="text-xs muted">
        {serviceName} — {envName}
      </div>

      <div className="text-sm text-slate-200">
        <div className="text-xs muted">AI Diagnosis</div>
        <div className="mt-1">{detail?.root_cause_summary ?? "—"}</div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-lg border border-white/10 bg-white/5 p-3">
          <div className="text-xs muted">Confidence</div>
          <div className="mt-1 text-lg font-semibold">
            {detail?.confidence != null ? `${Math.round(detail.confidence * 100)}%` : "—"}
          </div>
        </div>
        <div className="rounded-lg border border-white/10 bg-white/5 p-3">
          <div className="text-xs muted">Suggested Action</div>
          <div className="mt-1 text-sm">Rollback deployment</div>
        </div>
      </div>

      <div className="rounded-lg border border-white/10 bg-white/5 p-3">
        <div className="flex items-center justify-between">
          <div className="text-xs muted">Diagnostic Timeline</div>
          {events.length > 4 && onViewAllTimeline && (
            <button
              className="text-xs text-indigo-300 hover:text-indigo-200"
              onClick={onViewAllTimeline}
            >
              View All
            </button>
          )}
        </div>
        <div className="mt-2 space-y-2">
          {events.slice(0, 4).map((e) => (
            <div key={e.id} className="flex items-start justify-between gap-3 text-xs">
              <div className="text-slate-200">{e.message}</div>
              <div className="muted shrink-0">{formatTs(e.ts)}</div>
            </div>
          ))}
          {events.length === 0 && (
            <div className="text-xs muted">Select an incident to view details.</div>
          )}
        </div>
      </div>
    </div>
  );
}
