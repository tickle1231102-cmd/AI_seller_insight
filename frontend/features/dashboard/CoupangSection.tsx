import type { CoupangKpis, CoupangValues } from "@/types/api";
import { formatCount, formatPercent, formatWon } from "@/lib/format";
import { Delta, FunnelStep } from "@/features/dashboard/StoreSection";

const CANCEL_ALERT_PP = 5; // 전월 대비 취소율이 이만큼(%p) 오르면 옵션 행에 경고 표시

type Card = { label: string; value: string; delta: number | null; unit: string; goodWhenUp: boolean };

export function CoupangSection({ coupang }: { coupang: CoupangKpis }) {
  const { current: cur, previous: prev, change } = coupang;
  const p = (f: (v: CoupangValues) => string) => (prev ? f(prev) : undefined);

  const cards: Card[] = [
    { label: "방문자", value: formatCount(cur.visits, "명"), delta: change.visits_change, unit: "%", goodWhenUp: true },
    { label: "장바구니율", value: formatPercent(cur.cart_rate), delta: change.cart_rate_change_pp, unit: "%p", goodWhenUp: true },
    { label: "구매전환율", value: formatPercent(cur.conversion_rate), delta: change.conversion_rate_change_pp, unit: "%p", goodWhenUp: true },
    { label: "결제단가", value: cur.aov === null ? "-" : formatWon(cur.aov), delta: change.aov_change, unit: "%", goodWhenUp: true },
    { label: "취소율(수량)", value: formatPercent(cur.cancel_rate), delta: change.cancel_rate_change_pp, unit: "%p", goodWhenUp: false },
    { label: "취소 금액 비율", value: formatPercent(cur.cancel_amount_rate), delta: change.cancel_amount_rate_change_pp, unit: "%p", goodWhenUp: false },
  ];

  return (
    <section className="card store">
      <div className="card-head">
        <h2>쿠팡 판매 분석</h2>
        <span className="chip">{coupang.previous_period ? `${coupang.previous_period} vs ${coupang.period}` : coupang.period}</span>
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
        <FunnelStep label="방문자" value={formatCount(cur.visits, "명")} prev={p((v) => formatCount(v.visits, "명"))} />
        <div className="funnel-arrow">
          <span>장바구니 {formatPercent(cur.cart_rate)}</span>
          <Delta delta={change.cart_rate_change_pp} unit="%p" goodWhenUp />
        </div>
        <FunnelStep label="장바구니" value={formatCount(cur.cart_adds, "건")} prev={p((v) => formatCount(v.cart_adds, "건"))} />
        <div className="funnel-arrow">
          <span>전환 {formatPercent(cur.conversion_rate)}</span>
          <Delta delta={change.conversion_rate_change_pp} unit="%p" goodWhenUp />
        </div>
        <FunnelStep label="주문" value={formatCount(cur.orders, "건")} prev={p((v) => formatCount(v.orders, "건"))} />
        <div className="funnel-arrow">
          <span>총매출 {formatWon(cur.gross_revenue)}</span>
          <span className="muted">취소 −{formatWon(cur.cancel_amount)}</span>
        </div>
        <FunnelStep
          label="매출"
          value={formatWon(cur.revenue)}
          prev={p((v) => formatWon(v.revenue))}
          note={<Delta delta={change.revenue_change} unit="%" goodWhenUp />}
        />
      </div>

      <h3 className="sub-title">옵션별 성과 ({coupang.period}, 매출 상위 {coupang.products.length}개)</h3>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>옵션</th>
              <th>방문자</th>
              <th>장바구니율</th>
              <th>주문</th>
              <th>전환율</th>
              <th>매출</th>
              <th>결제단가</th>
              <th>취소율</th>
            </tr>
          </thead>
          <tbody>
            {coupang.products.map((r) => {
              const cancelAlert = r.cancel_rate_change_pp !== null && r.cancel_rate_change_pp >= CANCEL_ALERT_PP;
              return (
                <tr key={r.product_id}>
                  <td className="strong">
                    {r.product_name}
                    {cancelAlert && <span className="badge warn inline">취소 급증</span>}
                  </td>
                  <td>{formatCount(r.visits, "")}</td>
                  <td>{formatPercent(r.cart_rate)}</td>
                  <td>{formatCount(r.orders, "건")}</td>
                  <td>
                    {formatPercent(r.conversion_rate)}{" "}
                    <span className="small">
                      <Delta delta={r.conversion_rate_change_pp} unit="%p" goodWhenUp />
                    </span>
                  </td>
                  <td>{formatWon(r.revenue)}</td>
                  <td>{r.aov === null ? "-" : formatWon(r.aov)}</td>
                  <td>
                    {formatPercent(r.cancel_rate)}{" "}
                    <span className="small">
                      <Delta delta={r.cancel_rate_change_pp} unit="%p" goodWhenUp={false} />
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
