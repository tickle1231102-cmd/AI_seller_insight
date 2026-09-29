import type { Kpis } from "@/types/api";
import { formatCount, formatPercent, formatSignedPercent, formatWon } from "@/lib/format";

export function KpiCards({ kpis }: { kpis: Kpis }) {
  const { current, change } = kpis;
  const items = [
    { label: "매출", value: formatWon(current.revenue), delta: change.revenue_change, unit: "%", goodWhenUp: true },
    { label: "주문", value: formatCount(current.orders, "건"), delta: change.orders_change, unit: "%", goodWhenUp: true },
    { label: "판매량", value: formatCount(current.units, "개"), delta: change.units_change, unit: "%", goodWhenUp: true },
    { label: "광고비", value: formatWon(current.ad_spend), delta: change.ad_spend_change, unit: "%", goodWhenUp: false },
    { label: "광고매출", value: formatWon(current.ad_revenue), delta: change.ad_revenue_change, unit: "%", goodWhenUp: true },
    { label: "ROAS", value: formatPercent(current.roas), delta: change.roas_change_pp, unit: "%p", goodWhenUp: true },
  ];

  return (
    <section className="kpi-row">
      {items.map((it) => {
        const tone =
          it.delta === null || it.delta === 0 ? "" : (it.delta > 0) === it.goodWhenUp ? "up" : "down";
        return (
          <div key={it.label} className="card kpi">
            <span className="muted small">{it.label}</span>
            <strong className="kpi-value">{it.value}</strong>
            <span className="small">
              <span className={`delta ${tone}`}>{formatSignedPercent(it.delta, it.unit)}</span>
              <span className="muted"> 전월 대비</span>
            </span>
          </div>
        );
      })}
    </section>
  );
}
