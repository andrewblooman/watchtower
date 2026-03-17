import { Download, FileCode, FileJson, FileText } from "lucide-react";
import { S3Icon } from "@/components/icons/AwsIcons";

interface ArtifactListProps {
  filenames: string[];
  downloadUrl: (name: string) => string;
}

function fileIcon(name: string) {
  const ext = name.split(".").pop()?.toLowerCase();
  if (ext === "json") return <FileJson size={14} className="shrink-0 text-amber-300" />;
  if (ext === "md") return <FileText size={14} className="shrink-0 text-sky-300" />;
  return <FileCode size={14} className="shrink-0 text-slate-400" />;
}

export default function ArtifactList({ filenames, downloadUrl }: ArtifactListProps) {
  return (
    <div className="space-y-2">
      {filenames.slice(0, 8).map((name) => (
        <a
          key={name}
          className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm hover:bg-white/10 group"
          href={downloadUrl(name)}
          download
        >
          {fileIcon(name)}
          <span className="truncate font-mono text-xs text-indigo-300 group-hover:text-indigo-200 flex-1">{name}</span>
          <div className="shrink-0 flex items-center gap-1 opacity-60 group-hover:opacity-100">
            <S3Icon size={12} />
            <Download size={12} className="text-slate-400" />
          </div>
        </a>
      ))}
      {filenames.length === 0 && <div className="text-sm muted">No artifacts yet.</div>}
    </div>
  );
}

