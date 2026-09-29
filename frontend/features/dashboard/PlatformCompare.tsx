"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { PlatformComparison } from "@/types/api";
import { formatCount, formatPercent, formatWon, platformLabel } from "@/lib/format";

export function PlatformCompare({ data }: { data: PlatformComparison[] }) {
  const chartData = data.map((d) => ({ ...d, label: platformLabel(d.platform) }));
  return (
    <section className="card">
      <h2>플랫폼별 비교</h2>
      <div className="compare">
        <div className="chart">
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={chartData} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
              <CartesianGrid stroke="var(--border)" vertical={false} />
              <XAxis dataKey="label" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} tickFormatter={(v: number) => `${v}%`} />
              <Tooltip formatter={(v) => formatPercent(Number(v))} />
              <Bar dataKey="roas" name="ROAS" fill="var(--primary)" radius={[4, 4, 0, 0]} maxBarSize={56} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>플랫폼</th>
                <th>매출</th>
                <th>주문</th>
                <th>광고비</th>
                <th>ROAS</th>
              </tr>
            </thead>
            <tbody>
              {data.map((d) => (
                <tr key={d.platform}>
                  <td className="strong">{platformLabel(d.platform)}</td>
                  <td>{formatWon(d.revenue)}</td>
                  <td>{formatCount(d.orders, "건")}</td>
                  <td>{formatWon(d.ad_spend)}</td>
                  <td>{formatPercent(d.roas)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
