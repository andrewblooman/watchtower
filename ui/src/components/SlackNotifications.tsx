"use client";

import { SlackIcon } from "@/components/icons/SlackIcon";
import type { SessionListItem } from "@/lib/types";
import { formatAgo } from "@/lib/time";

export interface SlackNotification {
  id: string;
  ts: string;
  level: "alert" | "resolved" | "failed";
  title: string;
  body: string;
  repo: string;
  commit: string;
}

/** Derive Slack-style notifications from a list of investigation sessions. */
export function sessionNotifications(sessions: SessionListItem[]): SlackNotification[] {
  return sessions.map((s) => {
    const base = `${s.service_name} — ${s.github_repo}@${s.commit_short}`;
    if (s.status === "resolved") {
      return {
        id: s.session_id,
        ts: s.started_at,
        level: "resolved",
        title: "Investigation Resolved",
        body: `${base} in ${s.environment}. Root cause identified.`,
        repo: s.github_repo,
        commit: s.commit_short,
      };
    }
    if (s.status === "failed" || s.status === "timeout") {
      return {
        id: s.session_id,
        ts: s.started_at,
        level: "failed",
        title: `Investigation ${s.status === "timeout" ? "Timed Out" : "Failed"}`,
        body: `${base} in ${s.environment}. Manual investigation required.`,
        repo: s.github_repo,
        commit: s.commit_short,
      };
    }
    return {
      id: s.session_id,
      ts: s.started_at,
      level: "alert",
      title: "Investigation Alert",
      body: `${base} in ${s.environment}. Analysis in progress.`,
      repo: s.github_repo,
      commit: s.commit_short,
    };
  });
}

const levelStyles = {
  alert:    { bar: "bg-amber-500",   badge: "bg-amber-500/20 text-amber-200",   label: "🔔 Incident Alert" },
  resolved: { bar: "bg-emerald-500", badge: "bg-emerald-500/20 text-emerald-200", label: "✅ Resolved" },
  failed:   { bar: "bg-rose-500",    badge: "bg-rose-500/20 text-rose-200",     label: "❌ Failed" },
};

export default function SlackNotifications({ notifications }: { notifications: SlackNotification[] }) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <SlackIcon size={18} />
        <span className="text-sm font-semibold">Slack Notifications</span>
        <span className="ml-auto text-xs muted">{notifications.length} alerts</span>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {notifications.map((n) => {
          const s = levelStyles[n.level];
          return (
            <div key={n.id} className="flex gap-3 rounded-lg border border-white/10 bg-white/5 p-3 overflow-hidden relative">
              <div className={`absolute left-0 top-0 bottom-0 w-1 rounded-l-lg ${s.bar}`} />
              <div className="ml-2 min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${s.badge}`}>{s.label}</span>
                  <span className="text-xs muted ml-auto shrink-0">{formatAgo(n.ts)}</span>
                </div>
                <div className="mt-1.5 text-sm font-medium text-slate-200 truncate">{n.title}</div>
                <div className="mt-0.5 text-xs muted line-clamp-2">{n.body}</div>
                <div className="mt-1.5 font-mono text-xs text-indigo-300 truncate">{n.repo}@{n.commit}</div>
              </div>
            </div>
          );
        })}
        {notifications.length === 0 && (
          <div className="text-sm muted col-span-3">No notifications yet.</div>
        )}
      </div>
    </div>
  );
}

