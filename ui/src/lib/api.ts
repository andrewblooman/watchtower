import type {
  ArtifactRow,
  DashboardSummary,
  EventRow,
  FiltersResponse,
  IncidentDetail,
  IncidentRow
} from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return (await res.json()) as T;
}

export function fetchFilters(tenantId?: string): Promise<FiltersResponse> {
  const q = tenantId ? `?tenant_id=${encodeURIComponent(tenantId)}` : "";
  return getJson(`/v1/filters${q}`);
}

export function fetchDashboardSummary(scope: { tenantId: string; serviceId: string; environmentId: string }): Promise<DashboardSummary> {
  const q = `?tenant_id=${scope.tenantId}&service_id=${scope.serviceId}&environment_id=${scope.environmentId}`;
  return getJson(`/v1/dashboard/summary${q}`);
}

export function fetchIncidents(scope: { tenantId: string; serviceId: string; environmentId: string }): Promise<IncidentRow[]> {
  const q = `?tenant_id=${scope.tenantId}&service_id=${scope.serviceId}&environment_id=${scope.environmentId}&status=active`;
  return getJson(`/v1/incidents${q}`);
}

export function fetchIncident(id: string): Promise<IncidentDetail> {
  return getJson(`/v1/incidents/${id}`);
}

export function fetchEvents(
  scope: { tenantId: string; serviceId: string; environmentId: string },
  opts?: { incidentId?: string; limit?: number }
): Promise<EventRow[]> {
  const params = new URLSearchParams({
    tenant_id: scope.tenantId,
    service_id: scope.serviceId,
    environment_id: scope.environmentId,
    limit: String(opts?.limit ?? 200)
  });
  if (opts?.incidentId) params.set("incident_id", opts.incidentId);
  return getJson(`/v1/events?${params.toString()}`);
}

export function fetchArtifacts(opts: { runId?: string; incidentId?: string }): Promise<ArtifactRow[]> {
  const params = new URLSearchParams();
  if (opts.runId) params.set("run_id", opts.runId);
  if (opts.incidentId) params.set("incident_id", opts.incidentId);
  return getJson(`/v1/artifacts?${params.toString()}`);
}

