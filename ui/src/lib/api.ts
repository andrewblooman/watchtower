import type {
  CommandRecord,
  DashboardSummary,
  ReasoningTurn,
  SessionDetail,
  SessionListItem,
} from "@/lib/types";

// Empty string = same origin (when served by FastAPI).
// Override with NEXT_PUBLIC_API_BASE=http://localhost:8000 in ui/.env.local for local dev.
const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return (await res.json()) as T;
}

export function fetchSessions(status?: string): Promise<SessionListItem[]> {
  const q = status ? `?status=${encodeURIComponent(status)}` : "";
  return getJson(`/v1/sessions${q}`);
}

export function fetchSession(sessionId: string): Promise<SessionDetail> {
  return getJson(`/v1/sessions/${encodeURIComponent(sessionId)}`);
}

export function fetchCommands(sessionId: string): Promise<CommandRecord[]> {
  return getJson(`/v1/sessions/${encodeURIComponent(sessionId)}/commands`);
}

export function fetchReasoning(sessionId: string): Promise<ReasoningTurn[]> {
  return getJson(`/v1/sessions/${encodeURIComponent(sessionId)}/reasoning`);
}

export function fetchArtifacts(sessionId: string): Promise<string[]> {
  return getJson(`/v1/sessions/${encodeURIComponent(sessionId)}/artifacts`);
}

export function fetchDashboardSummary(): Promise<DashboardSummary> {
  return getJson("/v1/dashboard/summary");
}

export function artifactDownloadUrl(sessionId: string, filename: string): string {
  return `${API_BASE}/v1/sessions/${encodeURIComponent(sessionId)}/artifacts/${encodeURIComponent(filename)}/download`;
}
