import type { StoreKpis, StoreValues } from "@/types/api";
import { formatCount, formatPercent, formatSignedPercent, formatWon } from "@/lib/format";

const REFUND_ALERT_PP = 5; // 전월 대비 환불률이 이만큼(%p) 오르면 상품 행에 경고 표시

type Card = { label: string; value: string; delta: number | null; unit: string; goodWhenUp: boolean };

const tone = (delta: number | null, goodWhenUp: boolean) =>
  delta === null || delta === 0 ? "" : (delta > 0) === goodWhenUp ? "up" : "down";

function Delta({ delta, unit, goodWhenUp }: { delta: number | null; unit: string; goodWhenUp: boolean }) {
  return <span className={`delta ${tone(delta, goodWhenUp)}`}>{formatSignedPercent(delta, unit)}</span>;
}

function FunnelStep({ label, value, prev, note }: { label: string; value: string; prev?: string; note?: React.ReactNode }) {
  return (
    <div className="funnel-step">
      <span className="muted small">{label}</span>
      <strong className="kpi-value">{value}</strong>
      {prev && <span className="muted small">전월 {prev}</span>}
      {note && <span className="small">{note}</span>}
    </div>
  );
}

export function StoreSection({ store }: { store: StoreKpis }) {
  const { current: cur, previous: prev, change } = store;
  const p = (f: (v: StoreValues) => string) => (prev ? f(prev) : undefined);

  const cards: Card[] = [
    { label: "방문수", value: formatCount(cur.visits, "회"), delta: change.visits_change, unit: "%", goodWhenUp: true },
    { label: "구매전환율", value: formatPercent(cur.conversion_rate), delta: change.conversion_rate_change_pp, unit: "%p", goodWhenUp: true },
    { label: "결제단가", value: cur.aov === null ? "-" : formatWon(cur.aov), delta: change.aov_change, unit: "%", goodWhenUp: true },
    { label: "순매출 비율", value: formatPercent(cur.net_ratio), delta: change.net_ratio_change_pp, unit: "%p", goodWhenUp: true },
    { label: "환불률(건수)", value: formatPercent(cur.refund_rate), delta: change.refund_rate_change_pp, unit: "%p", goodWhenUp: false },
    { label: "할인율", value: formatPercent(cur.discount_rate), delta: change.discount_rate_change_pp, unit: "%p", goodWhenUp: false },
  ];

  return (
    <section className="card store">
      <div className="card-head">
        <h2>스마트스토어 판매 분석</h2>
        <span className="chip">{store.previous_period ? `${store.previous_period} vs ${store.period}` : store.period}</span>
      </div>

      <div className="kpi-row">
        {cards.map((c) => (
          <div key={c.label} className="kpi soft">
            <span className="muted small">{c.label}</span>
            <strong className="kpi-value">{c.value}</strong>
            <span className="small">
              <Delta delta={c.delta} unit={c.unit} goodWhenUp={c.goodWhenUp} />
              <span className="muted"> 전월 대비</span>
            </span>
          </div>
        ))}
      </div>

      <h3 className="sub-title">구매 퍼널</h3>
      <div className="funnel">
        <FunnelStep label="방문" value={formatCount(cur.visits, "회")} prev={p((v) => formatCount(v.visits, "회"))} />
        <div className="funnel-arrow">
          <span>전환 {formatPercent(cur.conversion_rate)}</span>
          <Delta delta={change.conversion_rate_change_pp} unit="%p" goodWhenUp />
        </div>
        <FunnelStep label="결제" value={formatCount(cur.orders, "건")} prev={p((v) => formatCount(v.orders, "건"))} />
        <div className="funnel-arrow">
          <span>결제단가 {cur.aov === null ? "-" : formatWon(cur.aov)}</span>
        </div>
        <FunnelStep label="총매출" value={formatWon(cur.gross_revenue)} prev={p((v) => formatWon(v.gross_revenue))} />
        <div className="funnel-arrow">
          <span>환불 −{formatWon(cur.refund_amount)}</span>
          <span className="muted">할인 {formatWon(cur.discount_amount)}</span>
        </div>
        <FunnelStep
          label="순매출"
          value={formatWon(cur.revenue)}
          prev={p((v) => formatWon(v.revenue))}
          note={<Delta delta={change.revenue_change} unit="%" goodWhenUp />}
        />
      </div>

      <h3 className="sub-title">상품별 성과 ({store.period}, 총매출 상위 {store.products.length}개)</h3>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>상품</th>
              <th>방문수</th>
              <th>결제</th>
              <th>전환율</th>
              <th>총매출</th>
              <th>순매출</th>
              <th>환불률</th>
              <th>할인율</th>
            </tr>
          </thead>
          <tbody>
            {store.products.map((r) => {
              const refundAlert = r.refund_rate_change_pp !== null && r.refund_rate_change_pp >= REFUND_ALERT_PP;
              return (
                <tr key={r.product_id}>
                  <td className="strong">
                    {r.product_name}
                    {refundAlert && <span className="badge warn inline">환불 급증</span>}
                  </td>
                  <td>{formatCount(r.visits, "")}</td>
                  <td>{formatCount(r.orders, "건")}</td>
                  <td>
                    {formatPercent(r.conversion_rate)}{" "}
                    <span className="small">
                      <Delta delta={r.conversion_rate_change_pp} unit="%p" goodWhenUp />
                    </span>
                  </td>
                  <td>{formatWon(r.gross_revenue)}</td>
                  <td>{formatWon(r.revenue)}</td>
                  <td>
                    {formatPercent(r.refund_rate)}{" "}
                    <span className="small">
                      <Delta delta={r.refund_rate_change_pp} unit="%p" goodWhenUp={false} />
                    </span>
                  </td>
                  <td>{formatPercent(r.discount_rate)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
