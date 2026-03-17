export type SessionMeta = {
  session_id: string;
  github_repo: string;
  commit_sha: string;
  commit_short: string;
  service_name: string;
  environment: string;
  started_at: string;
  status: string; // investigating | resolved | failed | timeout
  completed_at: string | null;
  event_metadata: Record<string, unknown>;
  source: string; // cache | s3
};

export type InvestigationSummary = {
  session_id: string;
  root_cause: string | null;
  confidence: number | null;
  recommendation: string | null;
  commands_count: number;
  reasoning_turns: number;
  resolution: string | null; // resolved | unresolved
};

export type CommandRecord = {
  ts: string;
  type: string; // shell | tool
  command: string;
  args: Record<string, unknown> | null;
  stdout: string | null;
  stderr: string | null;
  exit_code: number | null;
  result: unknown;
};

export type ReasoningTurn = {
  ts: string;
  turn: number;
  model: string;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  prompt_summary: string;
  response: string;
};

export type SessionListItem = {
  session_id: string;
  github_repo: string;
  commit_short: string;
  service_name: string;
  environment: string;
  started_at: string;
  status: string;
  source: string; // cache | s3
};

export type SessionDetail = {
  session: SessionMeta;
  summary: InvestigationSummary | null;
  commands_count: number;
  reasoning_turns: number;
  artifacts: string[];
};

export type DashboardSummary = {
  active_sessions: number;
  completed_sessions: number;
  total_sessions: number;
  recent_repos: string[];
};

export type EventRow = {
  id: string;
  ts: string;
  type: string;
  message: string;
  meta: Record<string, unknown>;
};

export type IncidentDetail = {
  root_cause_summary: string | null;
  confidence: number | null;
};

export type IdName = {
  id: string;
  name: string;
};

export type IncidentRow = {
  id: string;
  service: string;
  environment: string;
  status: string;
  root_cause_summary: string | null;
  detected_at: string;
};
