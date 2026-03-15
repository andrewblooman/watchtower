"use client";

import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import {
  ArtifactRow,
  DashboardSummary,
  EventRow,
  FiltersResponse,
  IncidentDetail,
  IncidentRow,
  IdName
} from "@/lib/types";
import {
  fetchArtifacts,
  fetchDashboardSummary,
  fetchEvents,
  fetchFilters,
  fetchIncident,
  fetchIncidents
} from "@/lib/api";
import { formatAgo, formatTs } from "@/lib/time";

const Charts = dynamic(() => import("@/components/charts"), { ssr: false });

function Select({
  label,
  value,
  onChange,
  options
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: IdName[];
}) {
  return (
    <label className="flex flex-col gap-1 text-xs">
      <span className="muted">{label}</span>
      <select
        className="h-10 rounded-lg border border-white/10 bg-slate-950/60 px-3 text-sm text-slate-100 outline-none focus:border-indigo-400/60"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {options.map((o) => (
          <option key={o.id} value={o.id}>
            {o.name}
          </option>
        ))}
      </select>
    </label>
  );
}

function Kpi({ title, value, tone }: { title: string; value: number; tone: "warn" | "ok" | "bad" | "llm" }) {
  const toneClasses =
    tone === "warn"
      ? "from-amber-500/15 to-amber-500/5 border-amber-500/20"
      : tone === "ok"
        ? "from-emerald-500/15 to-emerald-500/5 border-emerald-500/20"
        : tone === "bad"
          ? "from-rose-500/15 to-rose-500/5 border-rose-500/20"
          : "from-violet-500/15 to-violet-500/5 border-violet-500/20";
  return (
    <div className={`panel p-4 bg-gradient-to-br ${toneClasses}`}>
      <div className="text-xs muted">{title}</div>
      <div className="mt-1 text-3xl font-semibold tracking-tight">{value}</div>
    </div>
  );
}

export default function Page() {
  const [live, setLive] = useState(true);
  const [filters, setFilters] = useState<FiltersResponse | null>(null);
  const [tenantId, setTenantId] = useState<string>("");
  const [serviceId, setServiceId] = useState<string>("");
  const [environmentId, setEnvironmentId] = useState<string>("");

  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [incidents, setIncidents] = useState<IncidentRow[]>([]);
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);
  const [incidentDetail, setIncidentDetail] = useState<IncidentDetail | null>(null);
  const [incidentEvents, setIncidentEvents] = useState<EventRow[]>([]);
  const [events, setEvents] = useState<EventRow[]>([]);
  const [artifacts, setArtifacts] = useState<ArtifactRow[]>([]);

  const ready = Boolean(tenantId && serviceId && environmentId);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const f = await fetchFilters();
      if (cancelled) return;
      setFilters(f);
      setTenantId(f.tenants[0]?.id ?? "");
    })().catch(() => {
      /* ignore */
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!tenantId) return;
    let cancelled = false;
    (async () => {
      const f = await fetchFilters(tenantId);
      if (cancelled) return;
      setFilters(f);
      setServiceId(f.services[0]?.id ?? "");
      setEnvironmentId(f.environments[0]?.id ?? "");
      setSelectedIncidentId(null);
    })().catch(() => {
      /* ignore */
    });
    return () => {
      cancelled = true;
    };
  }, [tenantId]);

  const scope = useMemo(
    () => ({ tenantId, serviceId, environmentId }),
    [tenantId, serviceId, environmentId]
  );

  useEffect(() => {
    if (!ready) return;
    let cancelled = false;

    async function refresh() {
      const [s, inc, ev] = await Promise.all([
        fetchDashboardSummary(scope),
        fetchIncidents(scope),
        fetchEvents(scope, { limit: 400 })
      ]);
      if (cancelled) return;
      setSummary(s);
      setIncidents(inc);
      setEvents(ev);
      if (!selectedIncidentId && inc[0]?.id) setSelectedIncidentId(inc[0].id);
    }

    refresh().catch(() => {
      /* ignore */
    });
    if (!live) return () => {};
    const id = setInterval(() => refresh().catch(() => {}), 5000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [ready, scope, live, selectedIncidentId]);

  useEffect(() => {
    if (!ready || !selectedIncidentId) {
      setIncidentDetail(null);
      setIncidentEvents([]);
      setArtifacts([]);
      return;
    }
    let cancelled = false;
    (async () => {
      const detail = await fetchIncident(selectedIncidentId);
      const [ev, arts] = await Promise.all([
        fetchEvents(scope, { incidentId: selectedIncidentId, limit: 200 }),
        fetchArtifacts({ incidentId: selectedIncidentId })
      ]);
      if (cancelled) return;
      setIncidentDetail(detail);
      setIncidentEvents(ev);
      setArtifacts(arts);
    })().catch(() => {
      /* ignore */
    });
    return () => {
      cancelled = true;
    };
  }, [ready, selectedIncidentId, scope]);

  const slackEvents = useMemo(
    () => events.filter((e) => e.type === "slack_sent").slice(0, 3),
    [events]
  );

  const selectedTenant = filters?.tenants.find((t) => t.id === tenantId)?.name ?? "—";
  const selectedService = filters?.services.find((s) => s.id === serviceId)?.name ?? "—";
  const selectedEnv = filters?.environments.find((e) => e.id === environmentId)?.name ?? "—";

  return (
    <main className="mx-auto max-w-7xl px-6 py-8">
      <div className="flex items-start justify-between gap-6">
        <div>
          <div className="text-sm font-semibold tracking-wide text-white/80">AI Reliability Engineer Platform</div>
          <div className="mt-1 text-xs muted">Intelligent diagnostics & automated incident management</div>
        </div>
        <button
          className={`h-10 rounded-lg px-4 text-sm font-medium border ${
            live ? "border-emerald-400/30 bg-emerald-500/10 text-emerald-200" : "border-white/10 bg-white/5 text-slate-200"
          }`}
          onClick={() => setLive((v) => !v)}
        >
          {live ? "Live: On" : "Live: Paused"}
        </button>
      </div>

      <div className="mt-6 panel p-4">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <Select label="Tenant" value={tenantId} onChange={setTenantId} options={filters?.tenants ?? []} />
          <Select label="Service" value={serviceId} onChange={setServiceId} options={filters?.services ?? []} />
          <Select
            label="Environment"
            value={environmentId}
            onChange={setEnvironmentId}
            options={filters?.environments ?? []}
          />
        </div>
        <div className="mt-3 text-xs muted">
          Viewing: <span className="text-slate-200">{selectedTenant}</span> /{" "}
          <span className="text-slate-200">{selectedService}</span> / <span className="text-slate-200">{selectedEnv}</span>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-4">
        <Kpi title="Active Incidents" value={summary?.active_incidents ?? 0} tone="warn" />
        <Kpi title="Tests Executed Today" value={summary?.tests_executed_today ?? 0} tone="ok" />
        <Kpi title="Recent Rollbacks" value={summary?.recent_rollbacks ?? 0} tone="bad" />
        <Kpi title="LLM Insights Used" value={summary?.llm_insights_used ?? 0} tone="llm" />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="panel p-4 lg:col-span-2">
          <div className="flex items-center justify-between">
            <div className="text-sm font-semibold">Current Incidents</div>
            <div className="text-xs muted">{incidents.length} shown</div>
          </div>
          <div className="mt-3 overflow-hidden rounded-lg border border-white/10">
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
                    className={`cursor-pointer hover:bg-white/5 ${
                      selectedIncidentId === i.id ? "bg-indigo-500/10" : ""
                    }`}
                    onClick={() => setSelectedIncidentId(i.id)}
                  >
                    <td className="px-3 py-2 font-medium">{i.service}</td>
                    <td className="px-3 py-2">{i.environment}</td>
                    <td className="px-3 py-2">
                      <span className="rounded-md border border-white/10 bg-white/5 px-2 py-1 text-xs">
                        {i.status.replaceAll("_", " ")}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-slate-200/90">{i.root_cause_summary ?? "—"}</td>
                    <td className="px-3 py-2 muted">{formatAgo(i.detected_at)}</td>
                  </tr>
                ))}
                {!incidents.length ? (
                  <tr>
                    <td className="px-3 py-6 muted" colSpan={5}>
                      No incidents yet. Wait a moment for the agent to ingest events.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </div>

        <div className="panel p-4">
          <div className="text-sm font-semibold">Root Cause Analysis</div>
          <div className="mt-3 text-xs muted">{selectedService} — {selectedEnv}</div>
          <div className="mt-4 space-y-3">
            <div className="text-sm text-slate-200">
              <div className="muted text-xs">AI Diagnosis</div>
              <div className="mt-1">{incidentDetail?.root_cause_summary ?? "—"}</div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg border border-white/10 bg-white/5 p-3">
                <div className="text-xs muted">Confidence</div>
                <div className="mt-1 text-lg font-semibold">
                  {incidentDetail?.confidence != null ? `${Math.round(incidentDetail.confidence * 100)}%` : "—"}
                </div>
              </div>
              <div className="rounded-lg border border-white/10 bg-white/5 p-3">
                <div className="text-xs muted">Suggested Action</div>
                <div className="mt-1 text-sm">Rollback deployment</div>
              </div>
            </div>
            <div className="rounded-lg border border-white/10 bg-white/5 p-3">
              <div className="text-xs muted">Diagnostic Timeline</div>
              <div className="mt-2 space-y-2">
                {incidentEvents.slice(0, 4).map((e) => (
                  <div key={e.id} className="flex items-start justify-between gap-3 text-xs">
                    <div className="text-slate-200">{e.message}</div>
                    <div className="muted shrink-0">{formatTs(e.ts)}</div>
                  </div>
                ))}
                {!incidentEvents.length ? <div className="text-xs muted">Select an incident to view details.</div> : null}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="panel p-4">
          <div className="text-sm font-semibold">Test Execution Summary</div>
          <div className="mt-3 h-52">
            <Charts kind="tests" events={events} />
          </div>
        </div>
        <div className="panel p-4">
          <div className="text-sm font-semibold">LLM Usage Trends</div>
          <div className="mt-3 h-52">
            <Charts kind="llm" events={events} />
          </div>
        </div>
        <div className="panel p-4">
          <div className="text-sm font-semibold">Recent Artifacts</div>
          <div className="mt-3 space-y-2">
            {artifacts.slice(0, 4).map((a) => (
              <a
                key={a.id}
                className="flex items-center justify-between gap-3 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm hover:bg-white/10"
                href={`${process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000"}/v1/artifacts/${a.id}/download`}
                target="_blank"
              >
                <div className="min-w-0">
                  <div className="truncate">{a.name}</div>
                  <div className="text-xs muted truncate">{a.path_or_url}</div>
                </div>
                <div className="text-xs muted shrink-0">{formatAgo(a.created_at)}</div>
              </a>
            ))}
            {!artifacts.length ? <div className="text-sm muted">No artifacts yet.</div> : null}
          </div>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="panel p-4 lg:col-span-2">
          <div className="text-sm font-semibold">Activity Feed</div>
          <div className="mt-3 space-y-2">
            {events.slice(0, 8).map((e) => (
              <div key={e.id} className="flex items-start justify-between gap-4 rounded-lg border border-white/10 bg-white/5 px-3 py-2">
                <div className="min-w-0">
                  <div className="text-xs muted">{e.type}</div>
                  <div className="truncate text-sm text-slate-200">{e.message}</div>
                </div>
                <div className="text-xs muted shrink-0">{formatAgo(e.ts)}</div>
              </div>
            ))}
            {!events.length ? <div className="text-sm muted">Waiting for events…</div> : null}
          </div>
        </div>
        <div className="panel p-4">
          <div className="text-sm font-semibold">Slack Notifications</div>
          <div className="mt-3 space-y-2">
            {slackEvents.map((e) => (
              <div key={e.id} className="rounded-lg border border-white/10 bg-white/5 px-3 py-2">
                <div className="text-xs muted">Incident Alert</div>
                <div className="mt-1 text-sm text-slate-200">{e.message}</div>
              </div>
            ))}
            {!slackEvents.length ? <div className="text-sm muted">No notifications yet.</div> : null}
          </div>
        </div>
      </div>
    </main>
  );
}

