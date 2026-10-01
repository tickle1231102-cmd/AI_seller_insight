import type { Kpis } from "@/types/api";
import type { AnalysisMode } from "@/features/mode/mode";
import { formatCount, formatPercent, formatSignedPercent, formatWon } from "@/lib/format";

type Item = { label: string; value: string; delta: number | null; unit: string; goodWhenUp: boolean };

// 증감 null 은 전월 자료가 없을 때와, 전월 값이 0 이라 계산할 수 없을 때 모두 나온다.
const nullReason = (hasPrev: boolean) =>
  hasPrev ? "전월 대비 계산 불가 (기준값 0 등)" : "비교할 전월 자료가 없어요";

function Delta({ it, hasPrev }: { it: Item; hasPrev: boolean }) {
  const tone = it.delta === null || it.delta === 0 ? "" : (it.delta > 0) === it.goodWhenUp ? "up" : "down";
  return (
    <span className="small" title={it.delta === null ? nullReason(hasPrev) : undefined}>
      <span className={`delta ${tone}`}>{formatSignedPercent(it.delta, it.unit)}</span>
      <span className="muted"> 전월 대비</span>
    </span>
  );
}

export function KpiCards({ kpis, mode }: { kpis: Kpis; mode: AnalysisMode }) {
  const { current, change } = kpis;
  const sales: Item[] = [
    { label: "매출", value: formatWon(current.revenue), delta: change.revenue_change, unit: "%", goodWhenUp: true },
    { label: "주문", value: formatCount(current.orders, "건"), delta: change.orders_change, unit: "%", goodWhenUp: true },
    { label: "판매량", value: formatCount(current.units, "개"), delta: change.units_change, unit: "%", goodWhenUp: true },
  ];
  const ad: Item[] = [
    { label: "광고비", value: formatWon(current.ad_spend), delta: change.ad_spend_change, unit: "%", goodWhenUp: false },
    { label: "광고매출", value: formatWon(current.ad_revenue), delta: change.ad_revenue_change, unit: "%", goodWhenUp: true },
    { label: "ROAS", value: formatPercent(current.roas), delta: change.roas_change_pp, unit: "%p", goodWhenUp: true },
  ];
  const [main, sub] = mode === "sales" ? [sales, ad] : [ad, sales];

  return (
    <section className="kpis">
      <div className="kpi-row main">
        {main.map((it) => (
          <div key={it.label} className="card kpi">
            <span className="muted small">{it.label}</span>
            <strong className="kpi-value">{it.value}</strong>
            <Delta it={it} hasPrev={!!kpis.previous_period} />
          </div>
        ))}
      </div>
      <div className="kpi-sub">
        {sub.map((it) => (
          <div key={it.label} className="kpi-mini">
            <span className="muted small">{it.label}</span>
            <strong>{it.value}</strong>
            <Delta it={it} hasPrev={!!kpis.previous_period} />
          </div>
        ))}
      </div>
    </section>
  );
}
