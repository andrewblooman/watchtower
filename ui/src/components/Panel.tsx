import { type ReactNode } from "react";

interface PanelProps {
  children: ReactNode;
  className?: string;
}

export default function Panel({ children, className = "" }: PanelProps) {
  return <div className={`panel p-4 ${className}`}>{children}</div>;
}

export function PanelHeader({
  title,
  badge,
}: {
  title: string;
  badge?: ReactNode;
}) {
  return (
    <div className="flex items-center justify-between">
      <div className="text-sm font-semibold">{title}</div>
      {badge && <div>{badge}</div>}
    </div>
  );
}
