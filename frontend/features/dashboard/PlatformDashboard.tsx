"use client";

import { useId } from "react";
import type { Dashboard, DashboardPlatform, DashboardValues } from "@/types/api";
import type { AnalysisMode } from "@/features/mode/mode";
import { ADS, SALES, STORE, METRICS, SOURCE_LABEL, availableFields, deltaValue, label, metricValue, totalValue, unavailable } from "./dashboardMetrics";

export type DashboardView = "simple" | "detailed";

export function DashboardViewToggle({ value, onChange }: { value: DashboardView; onChange: (v: DashboardView) => void }) {
  return <div className="mode-toggle" role="group" aria-label="대시보드 정보량">
    <button type="button" className={value === "simple" ? "is-active" : ""} aria-pressed={value === "simple"} onClick={() => onChange("simple")}>간단보기</button>
    <button type="button" className={value === "detailed" ? "is-active" : ""} aria-pressed={value === "detailed"} onClick={() => onChange("detailed")}>자세히보기</button>
  </div>;
}

function MetricTable({ current, previous, change, fields, store = false }: { current: DashboardValues; previous: DashboardValues; change: DashboardValues; fields: string[]; store?: boolean }) {
  return <div className="table-wrap" tabIndex={0} aria-label={store ? "스마트스토어 상세 지표 표" : "판매 광고 상세 지표 표"}>
    <table><thead><tr><th>지표</th><th>기준 월</th><th>전월</th><th>전월 대비</th></tr></thead>
      <tbody>{fields.map((field) => <tr key={field}>
        <th scope="row">{store && field === "revenue" ? "순매출" : METRICS[field].label}</th>
        <td>{metricValue(field, current[field])}</td><td>{metricValue(field, previous[field])}</td><td>{deltaValue(field, change[field])}</td>
      </tr>)}</tbody></table>
  </div>;
}

function PlatformDetails({ data: p, mode }: { data: DashboardPlatform; mode: AnalysisMode }) {
  const fields = mode === "sales" ? [...SALES, ...ADS] : [...ADS, ...SALES];
  const hasCurrentStore = p.has_store && p.current.store_values.revenue != null;
  const maxMoney = Math.max(1, ...p.trend.flatMap((m) => [m.values.revenue ?? 0, m.values.ad_spend ?? 0]));
  return <div className="platform-details">
    <h3>판매·광고 상세</h3>
    <MetricTable current={p.current.values} previous={p.previous.values} change={p.change} fields={fields} />
    <p className="muted small">—는 자료 없음·누락 또는 계산 불가입니다. 실제 0은 0으로 표시합니다. 비율 증감은 %p, 금액·건수 증감은 %입니다.</p>
    <h3>월별 추이</h3>
    <div className="platform-money-trend" aria-label={`${label(p)} 월별 매출 광고비 비교`}>
      {p.trend.map((month) => <div key={month.period} className="money-month">
        <strong>{month.period}</strong>
        {["revenue", "ad_spend"].map((field) => <div key={field} className={`money-line ${field}`}>
          <span>{METRICS[field].label}</span><div className="money-track" aria-hidden="true"><div style={{ width: `${Math.max(0, month.values[field] ?? 0) / maxMoney * 100}%` }} /></div>
          <span>{metricValue(field, month.values[field])}</span>
        </div>)}
      </div>)}
    </div>
    <div className="table-wrap" tabIndex={0} aria-label={`${label(p)} 월별 지표 표`}><table>
      <thead><tr><th>월</th>{fields.map((f) => <th key={f}>{METRICS[f].label}</th>)}</tr></thead>
      <tbody>{p.trend.map((m) => <tr key={m.period}><th scope="row">{m.period}</th>{fields.map((f) => <td key={f}>{metricValue(f, m.values[f])}</td>)}</tr>)}</tbody>
    </table></div>
    {p.has_store && <>
      <h3>스마트스토어 판매 분석</h3>
      <p className="muted small">SALES 원자료의 총매출·순매출 기준입니다.{p.overlap_excluded ? " 같은 월 네이버 통합 템플릿과 겹치는 판매액은 플랫폼 요약에서 제외했습니다. 아래 상세와 요약의 자료 정의가 다를 수 있습니다." : ""}</p>
      <MetricTable current={p.current.store_values} previous={p.previous.store_values} change={p.store_change} fields={STORE} store />
      <h3>구매 퍼널</h3>
      {!hasCurrentStore && <p className="muted small">기준 월 판매 지표가 없거나 누락되었습니다.</p>}
      <div className="funnel">
        {["visits", "orders", "gross_revenue", "revenue"].map((f) => <div className="funnel-step" key={f}>
          <span>{f === "revenue" ? "순매출" : METRICS[f].label}</span>
          <strong className="kpi-value">{metricValue(f, p.current.store_values[f])}</strong>
          <span className="muted small">전월 {metricValue(f, p.previous.store_values[f])}</span>
          <span className="small">{deltaValue(f, p.store_change[f])}</span>
        </div>)}
      </div>
      <p className="muted small">구매전환율 {metricValue("conversion_rate", p.current.store_values.conversion_rate)} · 결제단가 {metricValue("aov", p.current.store_values.aov)} · 환불 {metricValue("refund_amount", p.current.store_values.refund_amount)} · 할인 {metricValue("discount_amount", p.current.store_values.discount_amount)}</p>
      <div className="table-wrap" tabIndex={0} aria-label="스마트스토어 월별 퍼널 지표"><table>
        <thead><tr><th>월</th>{["visits", "orders", "revenue", "conversion_rate"].map((f) => <th key={f}>{f === "revenue" ? "순매출" : METRICS[f].label}</th>)}</tr></thead>
        <tbody>{p.trend.map((m) => <tr key={m.period}><th scope="row">{m.period}</th>{["visits", "orders", "revenue", "conversion_rate"].map((f) => <td key={f}>{metricValue(f, m.store_values[f])}</td>)}</tr>)}</tbody>
      </table></div>
    </>}
    {p.products.map((group) => {
      const productFields = availableFields(group.items.map((r) => r.values), group.source === "smartstore_sales" ? STORE : fields);
      return <div key={group.source} className="platform-products">
        <h3>{SOURCE_LABEL[group.source] ?? group.source} 상품별 성과</h3>
        <p className="muted small">{p.current.period} · {METRICS[group.sort_key]?.label} 순 상위 {group.items.length}개 / 전체 {group.total}개</p>
        <div className="table-wrap" tabIndex={0} aria-label={`${SOURCE_LABEL[group.source]} 상품별 성과 표`}><table>
          <thead><tr><th>상품 / ID</th>{productFields.map((f) => <th key={f}>{group.source === "smartstore_sales" && f === "revenue" ? "순매출" : METRICS[f].label}</th>)}</tr></thead>
          <tbody>{group.items.map((r) => <tr key={r.product_id}>
            <th scope="row"><span>{r.product_name}</span><br /><span className="muted small">{r.product_id}</span>{r.change.refund_rate != null && r.change.refund_rate >= 5 && <span className="badge warn inline">환불 급증</span>}</th>
            {productFields.map((f) => <td key={f}>{metricValue(f, r.values[f])}{(f === "refund_rate" || f === "conversion_rate") && <div className="muted small">{deltaValue(f, r.change[f])}</div>}</td>)}
          </tr>)}</tbody>
        </table></div>
      </div>;
    })}
    {!p.products.length && <p className="muted">기준 월 상품별 자료가 없습니다.</p>}
    {p.platform === "naver" && <p className="muted small">네이버 광고 소재와 스마트스토어 판매 상품은 ID 체계가 달라 상품별로 합치지 않습니다.</p>}
  </div>;
}

function PlatformSection({ data: p, view, mode, collapsed, onToggle }: { data: DashboardPlatform; view: DashboardView; mode: AnalysisMode; collapsed: boolean; onToggle: () => void }) {
  const id = useId();
  const name = label(p);
  return <section className="card platform-section" aria-label={`${name} 분석`}>
    <div className="platform-heading"><div><h2>{name}</h2><p className="muted small">기준 {p.current.period} · 비교 {p.previous.period}</p></div>
      <button type="button" className="btn secondary" aria-expanded={!collapsed} aria-controls={id} aria-label={`${name} ${collapsed ? "펼치기" : "접기"}`} onClick={onToggle}>{collapsed ? "펼치기" : "접기"}</button>
    </div>
    {!p.current.has_data && <p className="notice warn">기준 월 자료 없음 · 업로드 월 {p.periods.join(", ")}</p>}
    {p.current.has_data && (!p.current.has_sales || !p.current.has_ads) && <p className="muted small">{!p.current.has_sales ? "판매 자료 없음" : ""}{!p.current.has_sales && !p.current.has_ads ? " · " : ""}{!p.current.has_ads ? "광고 자료 없음" : ""}</p>}
    {collapsed && <p className="platform-collapsed">매출액 {metricValue("revenue", p.current.values.revenue)} · 광고비 {metricValue("ad_spend", p.current.values.ad_spend)}</p>}
    <div id={id} hidden={collapsed}>
      {!collapsed && <>
        <div className="platform-primary">
          {["revenue", "ad_spend", "roas"].map((field) => <div className={`kpi soft metric-${field}`} key={field}>
            <span className="muted">{field === "revenue" && p.platform === "naver" ? "매출액(순)" : METRICS[field].label}</span>
            <strong className="kpi-value">{metricValue(field, p.current.values[field])}</strong>
            {p.current.values[field] == null && <span className="muted small">{unavailable(p, field)}</span>}
            <span className="small">전월 {metricValue(field, p.previous.values[field])}</span>
            <span className="small">전월 대비 {deltaValue(field, p.change[field])}</span>
          </div>)}
        </div>
        <p className="muted small platform-note">{p.platform === "coupang" ? "매출은 쿠팡 판매 원자료 기준이며, 광고매출은 총매출에 더하지 않습니다." : "매출은 판매금액(순) 기준입니다. 네이버 광고 지표는 플랫폼 합계로만 결합합니다."} 비용 증가는 그 자체로 성과 악화를 뜻하지 않습니다.</p>
        {!p.previous.has_data && <p className="muted small">비교할 전월 자료가 없습니다.</p>}
        {view === "detailed" && <PlatformDetails data={p} mode={mode} />}
      </>}
    </div>
  </section>;
}

export function PlatformDashboard({ data, view, mode, collapsed, onToggle }: { data: Dashboard; view: DashboardView; mode: AnalysisMode; collapsed: Record<string, boolean>; onToggle: (p: string) => void }) {
  return <div className="platform-dashboard">
    <section className="card dashboard-total" aria-label="전체 플랫폼 요약"><h2>전체 요약 <span className="muted small">{data.period}</span></h2>
      <div className="dashboard-total-values">{["revenue", "ad_spend"].map((f) => <div key={f}><span>{METRICS[f].label}</span><strong>{metricValue(f, totalValue(data.platforms, f))}</strong></div>)}</div>
      <p className="muted small">플랫폼 요약 합계 · 일부 플랫폼의 해당 월 지표가 없으면 합계를 표시하지 않습니다.</p>
    </section>
    <div className={`platform-grid ${view}`}>
      {data.platforms.map((p) => <PlatformSection key={p.platform} data={p} view={view} mode={mode} collapsed={!!collapsed[p.platform]} onToggle={() => onToggle(p.platform)} />)}
    </div>
  </div>;
}
