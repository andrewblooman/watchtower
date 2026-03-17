"use client";

import { useEffect, useMemo, useState } from "react";
import type {
  CommandRecord,
  DashboardSummary,
  ReasoningTurn,
  SessionDetail,
  SessionListItem,
} from "@/lib/types";
import {
  artifactDownloadUrl,
  fetchDashboardSummary,
  fetchCommands,
  fetchReasoning,
  fetchSession,
  fetchSessions,
} from "@/lib/api";
import {
  MOCK_COMMANDS,
  MOCK_REASONING,
  MOCK_SESSION_DETAIL,
  MOCK_SESSIONS,
  MOCK_SUMMARY,
} from "@/lib/mockData";
import { formatTs } from "@/lib/time";
import Panel, { PanelHeader } from "@/components/Panel";
import KpiCard from "@/components/KpiCard";
import SessionsTable from "@/components/SessionsTable";
import InvestigationPanel from "@/components/InvestigationPanel";
import ArtifactList from "@/components/ArtifactList";
import SlackNotifications, { sessionNotifications } from "@/components/SlackNotifications";
import { CommandChart, ReasoningChart } from "@/components/charts";
import { BedrockIcon, CloudWatchIcon, ECSIcon, S3Icon } from "@/components/icons/AwsIcons";
import { Activity, AlertTriangle, BrainCircuit, CheckCircle2, GitBranch, Terminal, Wrench } from "lucide-react";

async function tryFetch<T>(fn: () => Promise<T>, fallback: T): Promise<T> {
  try {
    return await fn();
  } catch {
    return fallback;
  }
}

/** Pick the right AWS icon for a command string */
function CommandIcon({ command, type }: { command: string; type: string }) {
  if (type === "shell") return <Terminal size={12} className="shrink-0 text-sky-400" />;
  if (command.startsWith("cloudwatch:")) return <CloudWatchIcon size={14} />;
  if (command.startsWith("ecs:")) return <ECSIcon size={14} />;
  if (command.startsWith("s3:")) return <S3Icon size={14} />;
  if (command.startsWith("bedrock:")) return <BedrockIcon size={14} />;
  return <Wrench size={12} className="shrink-0 text-violet-400" />;
}

export default function Page() {
  const [live, setLive] = useState(true);
  const [usingMock, setUsingMock] = useState(false);

  const [sessions, setSessions] = useState<SessionListItem[]>(MOCK_SESSIONS);
  const [summary, setSummary] = useState<DashboardSummary>(MOCK_SUMMARY);
  const [selectedId, setSelectedId] = useState<string | null>(MOCK_SESSIONS[0]?.session_id ?? null);
  const [sessionDetail, setSessionDetail] = useState<SessionDetail | null>(MOCK_SESSION_DETAIL);
  const [reasoning, setReasoning] = useState<ReasoningTurn[]>(MOCK_REASONING);
  const [commands, setCommands] = useState<CommandRecord[]>(MOCK_COMMANDS);

  // Initial load — try real API, fall back to mock
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const real = await tryFetch(() => fetchSessions(), null);
      if (cancelled) return;
      if (real !== null) {
        setUsingMock(false);
        setSessions(real);
        if (!selectedId && real[0]) setSelectedId(real[0].session_id);
      } else {
        setUsingMock(true);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  // Polling refresh
  useEffect(() => {
    if (usingMock) return;
    let cancelled = false;
    async function refresh() {
      const [sess, summ] = await Promise.all([
        tryFetch(() => fetchSessions(), MOCK_SESSIONS),
        tryFetch(() => fetchDashboardSummary(), MOCK_SUMMARY),
      ]);
      if (cancelled) return;
      setSessions(sess);
      setSummary(summ);
    }
    refresh();
    if (!live) return () => {};
    const id = setInterval(refresh, 5000);
    return () => { cancelled = true; clearInterval(id); };
  }, [live, usingMock]);

  // Load selected session detail + reasoning + commands
  useEffect(() => {
    if (usingMock) {
      setSessionDetail(selectedId ? MOCK_SESSION_DETAIL : null);
      setReasoning(selectedId ? MOCK_REASONING : []);
      setCommands(selectedId ? MOCK_COMMANDS : []);
      return;
    }
    if (!selectedId) { setSessionDetail(null); setReasoning([]); setCommands([]); return; }
    let cancelled = false;
    (async () => {
      const [detail, turns, cmds] = await Promise.all([
        tryFetch(() => fetchSession(selectedId), MOCK_SESSION_DETAIL),
        tryFetch(() => fetchReasoning(selectedId), MOCK_REASONING),
        tryFetch(() => fetchCommands(selectedId), MOCK_COMMANDS),
      ]);
      if (cancelled) return;
      setSessionDetail(detail);
      setReasoning(turns);
      setCommands(cmds);
    })();
    return () => { cancelled = true; };
  }, [selectedId, usingMock]);

  const selectedSession = useMemo(
    () => sessions.find((s) => s.session_id === selectedId) ?? null,
    [sessions, selectedId],
  );

  const artifacts = sessionDetail?.artifacts ?? [];
  const slackNotifications = useMemo(() => sessionNotifications(sessions), [sessions]);

  return (
    <main className="mx-auto max-w-7xl px-6 py-8">

      {/* ── Header ── */}
      <div className="flex items-center justify-between gap-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600/30 border border-indigo-500/30">
            <Activity size={22} className="text-indigo-300" />
          </div>
          <div>
            <div className="text-lg font-bold tracking-tight text-white">SRE Debugging Agent</div>
            <div className="text-xs muted">Ephemeral ECS investigation · results persisted to S3</div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {usingMock && (
            <span className="rounded-md border border-amber-400/30 bg-amber-500/10 px-2 py-1 text-xs text-amber-200">
              Mock data
            </span>
          )}
          <button
            className={`h-8 rounded-lg px-3 text-xs font-medium border transition-colors ${
              live
                ? "border-emerald-400/30 bg-emerald-500/10 text-emerald-200 hover:bg-emerald-500/15"
                : "border-white/10 bg-white/5 text-slate-300 hover:bg-white/10"
            }`}
            onClick={() => setLive((v) => !v)}
          >
            {live ? "● Live" : "○ Paused"}
          </button>
        </div>
      </div>

      {/* ── KPI row ── */}
      <div className="mt-6 grid grid-cols-2 gap-4 md:grid-cols-4">
        <KpiCard
          title="Active Sessions"
          value={summary.active_sessions}
          tone="warn"
          icon={<AlertTriangle size={18} />}
        />
        <KpiCard
          title="Completed"
          value={summary.completed_sessions}
          tone="ok"
          icon={<CheckCircle2 size={18} />}
        />
        <KpiCard
          title="Total Sessions"
          value={summary.total_sessions}
          tone="llm"
          icon={<BrainCircuit size={18} />}
        />
        <div className="panel p-4 bg-gradient-to-br from-slate-500/10 to-slate-500/5 border-slate-500/20">
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <div className="text-xs muted">Recent Repos</div>
              <div className="mt-1 space-y-1">
                {summary.recent_repos.slice(0, 2).map((r) => (
                  <div key={r} className="truncate text-xs text-slate-300 font-mono">{r}</div>
                ))}
                {summary.recent_repos.length === 0 && <div className="text-xs muted">—</div>}
              </div>
            </div>
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-500/20 text-slate-300">
              <GitBranch size={18} />
            </div>
          </div>
        </div>
      </div>

      {/* ── Main grid: Sessions table + RCA panel ── */}
      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Panel className="lg:col-span-2">
          <PanelHeader
            title="Investigation Sessions"
            badge={<span className="text-xs muted">{sessions.length} shown</span>}
          />
          <div className="mt-3">
            <SessionsTable sessions={sessions} selectedId={selectedId} onSelect={setSelectedId} />
          </div>
        </Panel>

        <Panel>
          <PanelHeader
            title="AI Investigation"
            badge={
              <div className="flex items-center gap-1.5">
                <BedrockIcon size={14} />
                <span className="text-xs muted">Bedrock</span>
              </div>
            }
          />
          <div className="mt-3">
            <InvestigationPanel detail={sessionDetail} reasoning={reasoning} />
          </div>
        </Panel>
      </div>

      {/* ── Charts row + Artifacts ── */}
      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Panel>
          <PanelHeader
            title="Command Execution"
            badge={
              <div className="flex items-center gap-1.5">
                <CloudWatchIcon size={14} />
                <ECSIcon size={14} />
              </div>
            }
          />
          <div className="mt-3 h-36">
            <CommandChart commands={commands} />
          </div>
        </Panel>

        <Panel>
          <PanelHeader
            title="Reasoning Turns"
            badge={
              <div className="flex items-center gap-1.5">
                <BedrockIcon size={14} />
                <span className="text-xs muted">per session</span>
              </div>
            }
          />
          <div className="mt-3 h-36">
            <ReasoningChart sessions={sessions} />
          </div>
        </Panel>

        <Panel>
          <PanelHeader
            title="Artifacts"
            badge={
              <div className="flex items-center gap-1.5">
                <S3Icon size={14} />
                <span className="text-xs muted">{artifacts.length} files</span>
              </div>
            }
          />
          <div className="mt-3">
            {artifacts.length > 0 && sessionDetail ? (
              <ArtifactList
                filenames={artifacts}
                downloadUrl={(name) => artifactDownloadUrl(sessionDetail.session.session_id, name)}
              />
            ) : (
              <div className="text-sm muted">
                {selectedId ? "No artifacts yet." : "Select a session to view artifacts."}
              </div>
            )}
          </div>
        </Panel>
      </div>

      {/* ── Slack Notifications ── */}
      <div className="mt-4">
        <Panel>
          <SlackNotifications notifications={slackNotifications} />
        </Panel>
      </div>

      {/* ── Command history (shown when session is selected) ── */}
      {sessionDetail && (
        <div className="mt-4">
          <Panel>
            <PanelHeader
              title="Command & Tool History"
              badge={<span className="text-xs muted">{commands.length} records</span>}
            />
            <div className="mt-3 space-y-2 max-h-64 overflow-y-auto">
              {commands.map((c, i) => (
                <div key={i} className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs">
                  <div className="flex items-center gap-2 mb-1">
                    <CommandIcon command={c.command} type={c.type} />
                    <span
                      className={`rounded px-1.5 py-0.5 font-mono text-xs ${
                        c.type === "shell"
                          ? "bg-sky-500/20 text-sky-300"
                          : "bg-violet-500/20 text-violet-300"
                      }`}
                    >
                      {c.type}
                    </span>
                    <span className="text-slate-200 font-mono truncate flex-1">{c.command}</span>
                    {c.exit_code != null && (
                      <span className={`ml-auto shrink-0 font-mono ${c.exit_code === 0 ? "text-emerald-400" : "text-rose-400"}`}>
                        exit {c.exit_code}
                      </span>
                    )}
                  </div>
                  {c.stdout && (
                    <pre className="muted whitespace-pre-wrap text-xs mt-1 line-clamp-2">{c.stdout}</pre>
                  )}
                  <div className="muted mt-1">{formatTs(c.ts)}</div>
                </div>
              ))}
              {commands.length === 0 && <div className="text-sm muted">No commands recorded.</div>}
            </div>
          </Panel>
        </div>
      )}

    </main>
  );
}

