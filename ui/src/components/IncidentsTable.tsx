import type { IncidentRow } from "@/lib/types";
import StatusPill from "@/components/StatusPill";
import { formatAgo } from "@/lib/time";

interface IncidentsTableProps {
  incidents: IncidentRow[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export default function IncidentsTable({ incidents, selectedId, onSelect }: IncidentsTableProps) {
  return (
    <div className="overflow-hidden rounded-lg border border-white/10">
      <table className="w-full text-left text-sm">
        <thead className="bg-white/5 text-xs text-slate-300">
          <tr>
            <th className="px-3 py-2">Service</th>
            <th className="px-3 py-2">Environment</th>
            <th className="px-3 py-2">Status</th>
            <th className="px-3 py-2">Root Cause</th>
            <th className="px-3 py-2">Detected</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/10">
          {incidents.map((i) => (
            <tr
              key={i.id}
              className={`cursor-pointer hover:bg-white/5 ${selectedId === i.id ? "bg-indigo-500/10" : ""}`}
              onClick={() => onSelect(i.id)}
            >
              <td className="px-3 py-2 font-medium">{i.service}</td>
              <td className="px-3 py-2">{i.environment}</td>
              <td className="px-3 py-2">
                <StatusPill status={i.status} />
              </td>
              <td className="px-3 py-2 text-slate-200/90">{i.root_cause_summary ?? "—"}</td>
              <td className="px-3 py-2 muted">{formatAgo(i.detected_at)}</td>
            </tr>
          ))}
          {incidents.length === 0 && (
            <tr>
              <td className="px-3 py-6 muted" colSpan={5}>
                No incidents yet. Wait a moment for the agent to ingest events.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
