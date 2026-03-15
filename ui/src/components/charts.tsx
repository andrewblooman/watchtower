"use client";

import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import type { EventRow } from "@/lib/types";

function countTests(events: EventRow[]) {
  const suites = ["unit", "smoke", "integration", "regression"];
  const counts: Record<string, number> = Object.fromEntries(suites.map((s) => [s, 0]));
  for (const e of events) {
    if (e.type !== "test_passed" && e.type !== "test_failed") continue;
    const suite = String((e.meta as any)?.suite ?? "unknown");
    if (counts[suite] == null) counts[suite] = 0;
    counts[suite] += 1;
  }
  return Object.entries(counts).map(([suite, count]) => ({ suite, count }));
}

function llmTrend(events: EventRow[]) {
  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const counts: Record<string, number> = Object.fromEntries(days.map((d) => [d, 0]));
  for (const e of events) {
    if (e.type !== "recommendation") continue;
    const d = new Date(e.ts).getDay(); // 0=Sun
    const name = days[(d + 6) % 7]; // shift so Mon index 0
    counts[name] += 1;
  }
  return days.map((d) => ({ day: d, insights: counts[d] }));
}

export default function Charts({ kind, events }: { kind: "tests" | "llm"; events: EventRow[] }) {
  const data = useMemo(() => (kind === "tests" ? countTests(events) : llmTrend(events)), [kind, events]);

  if (kind === "tests") {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
          <XAxis dataKey="suite" stroke="rgba(255,255,255,0.55)" fontSize={12} />
          <YAxis stroke="rgba(255,255,255,0.55)" fontSize={12} allowDecimals={false} />
          <Tooltip
            contentStyle={{ background: "rgba(2,6,23,0.95)", border: "1px solid rgba(255,255,255,0.1)" }}
          />
          <Bar dataKey="count" fill="rgba(99,102,241,0.75)" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    );
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data}>
        <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
        <XAxis dataKey="day" stroke="rgba(255,255,255,0.55)" fontSize={12} />
        <YAxis stroke="rgba(255,255,255,0.55)" fontSize={12} allowDecimals={false} />
        <Tooltip
          contentStyle={{ background: "rgba(2,6,23,0.95)", border: "1px solid rgba(255,255,255,0.1)" }}
        />
        <Line type="monotone" dataKey="insights" stroke="rgba(236,72,153,0.85)" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

