export type IdName = { id: string; name: string };

export type FiltersResponse = {
  tenants: IdName[];
  services: IdName[];
  environments: IdName[];
};

export type DashboardSummary = {
  active_incidents: number;
  tests_executed_today: number;
  recent_rollbacks: number;
  llm_insights_used: number;
};

export type IncidentRow = {
  id: string;
  service: string;
  environment: string;
  status: string;
  title: string;
  root_cause_summary: string | null;
  detected_at: string;
};

export type IncidentDetail = {
  id: string;
  tenant_id: string;
  service_id: string;
  environment_id: string;
  run_id: string;
  status: string;
  title: string;
  root_cause_summary: string | null;
  confidence: number | null;
  detected_at: string;
  resolved_at: string | null;
};

export type EventRow = {
  id: string;
  ts: string;
  type: string;
  message: string;
  meta: Record<string, unknown>;
  run_id: string;
  incident_id: string | null;
};

export type ArtifactRow = {
  id: string;
  kind: string;
  name: string;
  path_or_url: string;
  created_at: string;
  run_id: string;
  incident_id: string | null;
};

