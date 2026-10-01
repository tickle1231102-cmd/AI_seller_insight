"use client";

import { Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { TrendPoint } from "@/types/api";
import type { AnalysisMode } from "@/features/mode/mode";
import { formatPercent, formatWon } from "@/lib/format";

// 응답의 trend 에는 매출·ROAS 만 있다 (#29). 모드에 따라 주가 되는 쪽만 강조한다.
export function TrendChart({ trend, mode }: { trend: TrendPoint[]; mode: AnalysisMode }) {
  const faded = 0.35;
  return (
    <section className="card">
      <h2>매출 · ROAS 추이</h2>
      <div className="chart">
        <ResponsiveContainer width="100%" height={260}>
          <ComposedChart data={trend} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
            <CartesianGrid stroke="var(--border)" vertical={false} />
            <XAxis dataKey="period" tick={{ fontSize: 12 }} />
            <YAxis
              yAxisId="rev"
              tick={{ fontSize: 12 }}
              tickFormatter={(v: number) => `${(v / 10000).toLocaleString("ko-KR")}만`}
            />
            <YAxis yAxisId="roas" orientation="right" tick={{ fontSize: 12 }} tickFormatter={(v: number) => `${v}%`} />
            <Tooltip
              formatter={(v, name) => (name === "매출" ? formatWon(Number(v)) : formatPercent(Number(v)))}
            />
            <Legend />
            <Bar
              yAxisId="rev"
              dataKey="revenue" name="매출" fill="var(--primary)" radius={[4, 4, 0, 0]} maxBarSize={48}
              fillOpacity={mode === "sales" ? 1 : faded}
            />
            <Line
              yAxisId="roas"
              dataKey="roas" name="ROAS" stroke="var(--warn)"
              strokeWidth={mode === "ad" ? 3 : 2}
              strokeOpacity={mode === "ad" ? 1 : faded}
              dot
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
