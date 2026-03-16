import type { ArtifactRow } from "@/lib/types";
import { formatAgo } from "@/lib/time";

interface ArtifactListProps {
  artifacts: ArtifactRow[];
  apiBase: string;
}

export default function ArtifactList({ artifacts, apiBase }: ArtifactListProps) {
  return (
    <div className="space-y-2">
      {artifacts.slice(0, 4).map((a) => (
        <a
          key={a.id}
          className="flex items-center justify-between gap-3 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm hover:bg-white/10"
          href={`${apiBase}/v1/artifacts/${a.id}/download`}
          target="_blank"
          rel="noreferrer"
        >
          <div className="min-w-0">
            <div className="truncate">{a.name}</div>
            <div className="text-xs muted truncate">{a.path_or_url}</div>
          </div>
          <div className="text-xs muted shrink-0">{formatAgo(a.created_at)}</div>
        </a>
      ))}
      {artifacts.length === 0 && <div className="text-sm muted">No artifacts yet.</div>}
    </div>
  );
}
