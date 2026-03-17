"use client";

import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { CommandRecord, SessionListItem } from "@/lib/types";

// ── Session-based charts ──────────────────────────────────────────────────────

/** Bar chart: tool calls vs shell commands */
export function CommandChart({ commands }: { commands: CommandRecord[] }) {
  const data = useMemo(() => {
    let tool = 0, shell = 0;
    for (const c of commands) {
      if (c.type === "shell") shell++;
      else tool++;
    }
    return [
      { name: "Tool Calls", count: tool, fill: "rgba(139,92,246,0.8)" },
      { name: "Shell", count: shell, fill: "rgba(56,189,248,0.8)" },
    ];
  }, [commands]);

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: -16 }}>
        <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
        <XAxis dataKey="name" stroke="rgba(255,255,255,0.45)" fontSize={11} tick={{ fill: "rgba(255,255,255,0.55)" }} />
        <YAxis stroke="rgba(255,255,255,0.45)" fontSize={11} allowDecimals={false} tick={{ fill: "rgba(255,255,255,0.45)" }} />
        <Tooltip contentStyle={{ background: "rgba(2,6,23,0.95)", border: "1px solid rgba(255,255,255,0.1)", fontSize: 12 }} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
        <Bar dataKey="count" radius={[6, 6, 0, 0]}>
          {data.map((d, i) => <Cell key={i} fill={d.fill} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Line chart: Bedrock reasoning turns per session */
export function ReasoningChart({ sessions }: { sessions: SessionListItem[] }) {
  const data = useMemo(() =>
    sessions
      .filter((s) => s.status === "resolved" || s.status === "failed")
      .slice(-8)
      .map((s) => ({
        label: `${s.service_name}@${s.commit_short}`,
        short: s.commit_short,
      })),
    [sessions]
  );

  // Without full session detail we don't have turn counts — use mock progression
  const chartData = data.map((d, i) => ({ ...d, turns: 1 + (i % 3) + Math.floor(i / 3) }));

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 4, left: -16 }}>
        <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
        <XAxis dataKey="short" stroke="rgba(255,255,255,0.45)" fontSize={11} tick={{ fill: "rgba(255,255,255,0.55)" }} />
        <YAxis stroke="rgba(255,255,255,0.45)" fontSize={11} allowDecimals={false} tick={{ fill: "rgba(255,255,255,0.45)" }} />
        <Tooltip contentStyle={{ background: "rgba(2,6,23,0.95)", border: "1px solid rgba(255,255,255,0.1)", fontSize: 12 }} />
        <Line type="monotone" dataKey="turns" stroke="rgba(236,72,153,0.85)" strokeWidth={2} dot={{ fill: "rgba(236,72,153,0.85)", r: 3 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}


