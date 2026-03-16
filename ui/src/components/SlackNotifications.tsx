import type { EventRow } from "@/lib/types";
import { formatAgo } from "@/lib/time";

interface SlackNotificationsProps {
  events: EventRow[];
}

export default function SlackNotifications({ events }: SlackNotificationsProps) {
  return (
    <div className="space-y-2">
      {events.map((e) => (
        <div key={e.id} className="rounded-lg border border-white/10 bg-white/5 px-3 py-2">
          <div className="flex items-center justify-between gap-2">
            <div className="text-xs muted">Incident Alert</div>
            <div className="text-xs muted shrink-0">{formatAgo(e.ts)}</div>
          </div>
          <div className="mt-1 text-sm text-slate-200">{e.message}</div>
        </div>
      ))}
      {events.length === 0 && <div className="text-sm muted">No notifications yet.</div>}
    </div>
  );
}
