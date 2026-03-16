"use client";

import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import type {
  ArtifactRow,
  DashboardSummary,
  EventRow,
  FiltersResponse,
  IncidentDetail,
  IncidentRow,
} from "@/lib/types";
import {
  fetchArtifacts,
  fetchDashboardSummary,
  fetchEvents,
  fetchFilters,
  fetchIncident,
  fetchIncidents,
} from "@/lib/api";
import {
  MOCK_ARTIFACTS,
  MOCK_EVENTS,
  MOCK_FILTERS,
  MOCK_INCIDENT_DETAIL,
  MOCK_INCIDENTS,
  MOCK_SUMMARY,
} from "@/lib/mockData";
import Panel, { PanelHeader } from "@/components/Panel";
import KpiCard from "@/components/KpiCard";
import FilterSelect from "@/components/FilterSelect";
import IncidentsTable from "@/components/IncidentsTable";
import RcaPanel from "@/components/RcaPanel";
import ArtifactList from "@/components/ArtifactList";
import SlackNotifications from "@/components/SlackNotifications";

const Charts = dynamic(() => import("@/components/charts"), { ssr: false });

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function tryFetch<T>(fn: () => Promise<T>, fallback: T): Promise<T> {
  try {
    return await fn();
  } catch {
    return fallback;
  }
}

export default function Page() {
  const [live, setLive] = useState(true);
  const [usingMock, setUsingMock] = useState(false);
  const [filters, setFilters] = useState<FiltersResponse>(MOCK_FILTERS);
  const [tenantId, setTenantId] = useState<string>(MOCK_FILTERS.tenants[0]?.id ?? "");
  const [serviceId, setServiceId] = useState<string>(MOCK_FILTERS.services[0]?.id ?? "");
  const [environmentId, setEnvironmentId] = useState<string>(MOCK_FILTERS.environments[0]?.id ?? "");

  const [summary, setSummary] = useState<DashboardSummary>(MOCK_SUMMARY);
  const [incidents, setIncidents] = useState<IncidentRow[]>(MOCK_INCIDENTS);
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(MOCK_INCIDENTS[0]?.id ?? null);
  const [incidentDetail, setIncidentDetail] = useState<IncidentDetail | null>(MOCK_INCIDENT_DETAIL);
  const [incidentEvents, setIncidentEvents] = useState<EventRow[]>(
    MOCK_EVENTS.filter((e) => e.incident_id === MOCK_INCIDENTS[0]?.id)
  );
  const [events, setEvents] = useState<EventRow[]>(MOCK_EVENTS);
  const [artifacts, setArtifacts] = useState<ArtifactRow[]>(MOCK_ARTIFACTS);

  // Load real filters; fall back to mock if API is unreachable
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const real = await tryFetch(() => fetchFilters(), null);
      if (cancelled) return;
      if (real) {
        setUsingMock(false);
        setFilters(real);
        setTenantId(real.tenants[0]?.id ?? "");
      } else {
        setUsingMock(true);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!tenantId || usingMock) return;
    let cancelled = false;
    (async () => {
      const f = await tryFetch(() => fetchFilters(tenantId), MOCK_FILTERS);
      if (cancelled) return;
      setFilters(f);
      setServiceId(f.services[0]?.id ?? "");
      setEnvironmentId(f.environments[0]?.id ?? "");
      setSelectedIncidentId(null);
    })();
    return () => { cancelled = true; };
  }, [tenantId, usingMock]);

  const scope = useMemo(
    () => ({ tenantId, serviceId, environmentId }),
    [tenantId, serviceId, environmentId]
  );

  const ready = Boolean(tenantId && serviceId && environmentId);

  useEffect(() => {
    if (usingMock) return;
    if (!ready) return;
    let cancelled = false;

    async function refresh() {
      const [s, inc, ev] = await Promise.all([
        tryFetch(() => fetchDashboardSummary(scope), MOCK_SUMMARY),
        tryFetch(() => fetchIncidents(scope), MOCK_INCIDENTS),
        tryFetch(() => fetchEvents(scope, { limit: 400 }), MOCK_EVENTS),
      ]);
      if (cancelled) return;
      setSummary(s);
      setIncidents(inc);
      setEvents(ev);
      if (!selectedIncidentId && inc[0]?.id) setSelectedIncidentId(inc[0].id);
    }

    refresh();
    if (!live) return () => {};
    const id = setInterval(() => refresh(), 5000);
    return () => { cancelled = true; clearInterval(id); };
  }, [ready, scope, live, selectedIncidentId, usingMock]);

  useEffect(() => {
    if (usingMock) {
      setIncidentDetail(selectedIncidentId ? MOCK_INCIDENT_DETAIL : null);
      setIncidentEvents(
        selectedIncidentId
          ? MOCK_EVENTS.filter((e) => e.incident_id === selectedIncidentId)
          : []
      );
      setArtifacts(
        selectedIncidentId
          ? MOCK_ARTIFACTS.filter((a) => a.incident_id === selectedIncidentId)
          : MOCK_ARTIFACTS
      );
      return;
    }

    if (!ready || !selectedIncidentId) {
      setIncidentDetail(null);
      setIncidentEvents([]);
      setArtifacts([]);
      return;
    }
    let cancelled = false;
    (async () => {
      const detail = await tryFetch(() => fetchIncident(selectedIncidentId), MOCK_INCIDENT_DETAIL);
      const [ev, arts] = await Promise.all([
        tryFetch(() => fetchEvents(scope, { incidentId: selectedIncidentId, limit: 200 }), []),
        tryFetch(() => fetchArtifacts({ incidentId: selectedIncidentId }), []),
      ]);
      if (cancelled) return;
      setIncidentDetail(detail);
      setIncidentEvents(ev);
      setArtifacts(arts);
    })();
    return () => { cancelled = true; };
  }, [ready, selectedIncidentId, scope, usingMock]);

  const slackEvents = useMemo(
    () => events.filter((e) => e.type === "slack_sent").slice(0, 3),
    [events]
  );

  const selectedTenant = filters.tenants.find((t) => t.id === tenantId)?.name ?? "—";
  const selectedService = filters.services.find((s) => s.id === serviceId)?.name ?? "—";
  const selectedEnv = filters.environments.find((e) => e.id === environmentId)?.name ?? "—";

  return (
    <main className="mx-auto max-w-7xl px-6 py-8">
      {/* Header */}
      <div className="flex items-start justify-between gap-6">
        <div>
          <div className="text-sm font-semibold tracking-wide text-white/80">
            AI Reliability Engineer Platform
          </div>
          <div className="mt-1 text-xs muted">
            Intelligent diagnostics &amp; automated incident management
          </div>
        </div>
        <div className="flex items-center gap-3">
          {usingMock && (
            <span className="rounded-md border border-amber-400/30 bg-amber-500/10 px-2 py-1 text-xs text-amber-200">
              Mock data
            </span>
          )}
          <button
            className={`h-10 rounded-lg px-4 text-sm font-medium border ${
              live
                ? "border-emerald-400/30 bg-emerald-500/10 text-emerald-200"
                : "border-white/10 bg-white/5 text-slate-200"
            }`}
            onClick={() => setLive((v) => !v)}
          >
            {live ? "Live: On" : "Live: Paused"}
          </button>
        </div>
      </div>

      {/* Filter bar */}
      <Panel className="mt-6">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <FilterSelect label="Tenant" value={tenantId} onChange={setTenantId} options={filters.tenants} />
          <FilterSelect label="Service" value={serviceId} onChange={setServiceId} options={filters.services} />
          <FilterSelect
            label="Environment"
            value={environmentId}
            onChange={setEnvironmentId}
            options={filters.environments}
          />
        </div>
        <div className="mt-3 text-xs muted">
          Viewing: <span className="text-slate-200">{selectedTenant}</span> /{" "}
          <span className="text-slate-200">{selectedService}</span> /{" "}
          <span className="text-slate-200">{selectedEnv}</span>
        </div>
      </Panel>

      {/* KPI row */}
      <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-4">
        <KpiCard title="Active Incidents" value={summary.active_incidents} tone="warn" />
        <KpiCard title="Tests Executed Today" value={summary.tests_executed_today} tone="ok" />
        <KpiCard title="Recent Rollbacks" value={summary.recent_rollbacks} tone="bad" />
        <KpiCard title="LLM Insights Used" value={summary.llm_insights_used} tone="llm" />
      </div>

      {/* Main grid: Incidents + RCA */}
      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Panel className="lg:col-span-2">
          <PanelHeader
            title="Current Incidents"
            badge={<span className="text-xs muted">{incidents.length} shown</span>}
          />
          <div className="mt-3">
            <IncidentsTable
              incidents={incidents}
              selectedId={selectedIncidentId}
              onSelect={setSelectedIncidentId}
            />
          </div>
        </Panel>

        <Panel>
          <PanelHeader title="Root Cause Analysis" />
          <div className="mt-3">
            <RcaPanel
              detail={incidentDetail}
              events={incidentEvents}
              serviceName={selectedService}
              envName={selectedEnv}
            />
          </div>
        </Panel>
      </div>

      {/* Charts row */}
      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Panel>
          <PanelHeader title="Test Execution Summary" />
          <div className="mt-3 h-52">
            <Charts kind="tests" events={events} />
          </div>
        </Panel>
        <Panel>
          <PanelHeader title="LLM Usage Trends" />
          <div className="mt-3 h-52">
            <Charts kind="llm" events={events} />
          </div>
        </Panel>
      </div>

      {/* Bottom row */}
      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Panel>
          <PanelHeader title="Slack Notifications" />
          <div className="mt-3">
            <SlackNotifications events={slackEvents} />
          </div>
        </Panel>

        <Panel>
          <PanelHeader title="Activity Feed" />
          <div className="mt-3 space-y-2">
            {events.slice(0, 5).map((e) => (
              <div
                key={e.id}
                className="flex items-start justify-between gap-4 rounded-lg border border-white/10 bg-white/5 px-3 py-2"
              >
                <div className="min-w-0">
                  <div className="text-xs muted">{e.type}</div>
                  <div className="truncate text-sm text-slate-200">{e.message}</div>
                </div>
              </div>
            ))}
            {events.length === 0 && <div className="text-sm muted">Waiting for events…</div>}
          </div>
        </Panel>

        <Panel>
          <PanelHeader
            title="Recent Artifacts"
            badge={
              artifacts.length > 4 ? (
                <button className="text-xs text-indigo-300 hover:text-indigo-200">View All</button>
              ) : undefined
            }
          />
          <div className="mt-3">
            <ArtifactList artifacts={artifacts} apiBase={API_BASE} />
          </div>
        </Panel>
      </div>
    </main>
  );
}
