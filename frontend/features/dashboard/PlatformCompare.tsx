"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { PlatformComparison } from "@/types/api";
import type { AnalysisMode } from "@/features/mode/mode";
import { formatCount, formatPercent, formatWon, platformLabel } from "@/lib/format";

type Column = { key: string; label: string; render: (d: PlatformComparison) => string };

const SALES_COLS: Column[] = [
  { key: "revenue", label: "매출", render: (d) => formatWon(d.revenue) },
  { key: "orders", label: "주문", render: (d) => formatCount(d.orders, "건") },
];
const AD_COLS: Column[] = [
  { key: "ad_spend", label: "광고비", render: (d) => formatWon(d.ad_spend) },
  { key: "ad_revenue", label: "광고매출", render: (d) => formatWon(d.ad_revenue) },
  { key: "roas", label: "ROAS", render: (d) => formatPercent(d.roas) },
];

export function PlatformCompare({ data, mode }: { data: PlatformComparison[]; mode: AnalysisMode }) {
  const chartData = data.map((d) => ({ ...d, label: platformLabel(d.platform) }));
  const cols = mode === "sales" ? [...SALES_COLS, ...AD_COLS] : [...AD_COLS, ...SALES_COLS];
  const isSales = mode === "sales";
  return (
    <section className="card">
      <h2>플랫폼별 비교</h2>
      <div className="compare">
        <div className="chart">
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={chartData} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
              <CartesianGrid stroke="var(--border)" vertical={false} />
              <XAxis dataKey="label" tick={{ fontSize: 12 }} />
              <YAxis
                tick={{ fontSize: 12 }}
                tickFormatter={(v: number) =>
                  isSales ? `${(v / 10000).toLocaleString("ko-KR")}만` : `${v}%`
                }
              />
              <Tooltip formatter={(v) => (isSales ? formatWon(Number(v)) : formatPercent(Number(v)))} />
              <Bar
                dataKey={isSales ? "revenue" : "roas"}
                name={isSales ? "매출" : "ROAS"}
                fill="var(--primary)"
                radius={[4, 4, 0, 0]}
                maxBarSize={56}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>플랫폼</th>
                {cols.map((c) => (
                  <th key={c.key}>{c.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.map((d) => (
                <tr key={d.platform}>
                  <td className="strong">{platformLabel(d.platform)}</td>
                  {cols.map((c) => (
                    <td key={c.key}>{c.render(d)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
