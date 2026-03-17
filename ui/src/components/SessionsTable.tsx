import type { SessionListItem } from "@/lib/types";
import StatusPill from "@/components/StatusPill";
import { formatAgo } from "@/lib/time";

interface SessionsTableProps {
  sessions: SessionListItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export default function SessionsTable({ sessions, selectedId, onSelect }: SessionsTableProps) {
  return (
    <div className="overflow-hidden rounded-lg border border-white/10">
      <table className="w-full text-left text-sm">
        <thead className="bg-white/5 text-xs text-slate-300">
          <tr>
            <th className="px-3 py-2">Repository</th>
            <th className="px-3 py-2">Commit</th>
            <th className="px-3 py-2">Service</th>
            <th className="px-3 py-2">Environment</th>
            <th className="px-3 py-2">Status</th>
            <th className="px-3 py-2">Started</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/10">
          {sessions.map((s) => (
            <tr
              key={s.session_id}
              className={`cursor-pointer hover:bg-white/5 ${
                selectedId === s.session_id ? "bg-indigo-500/10" : ""
              }`}
              onClick={() => onSelect(s.session_id)}
            >
              <td className="px-3 py-2 font-medium">{s.github_repo}</td>
              <td className="px-3 py-2 font-mono text-xs text-slate-300">{s.commit_short}</td>
              <td className="px-3 py-2">{s.service_name}</td>
              <td className="px-3 py-2">{s.environment}</td>
              <td className="px-3 py-2">
                <StatusPill status={s.status} />
              </td>
              <td className="px-3 py-2 muted">{formatAgo(s.started_at)}</td>
            </tr>
          ))}
          {sessions.length === 0 && (
            <tr>
              <td className="px-3 py-6 muted" colSpan={6}>
                No sessions yet  waiting for an investigation to start.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
