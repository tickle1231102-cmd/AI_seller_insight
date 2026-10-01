import type { Insight } from "@/types/api";

import { platformLabel } from "@/lib/format";

export const EXAMPLE_QUESTIONS = [
  "광고 효율이 가장 안 좋은 플랫폼 어디야?",
  "이번 달 매출이 가장 높은 상품은?",
  "광고비가 가장 많이 늘어난 플랫폼은?",
];

const COLUMN_LABEL: Record<string, string> = {
  rank: "순위",
  score: "충족 조건 수",
  evaluated_rules: "확인 가능 조건 수",
  data_scope: "자료 구분",
  platform: "플랫폼",
  period: "기간",
  product_name: "상품",
  revenue: "매출",
  orders: "주문",
  units: "판매량",
  ad_spend: "광고비",
  ad_revenue: "광고매출",
  roas: "ROAS",
  revenue_previous: "전월 매출",
  orders_previous: "전월 주문",
  units_previous: "전월 판매량",
  ad_spend_previous: "전월 광고비",
  ad_revenue_previous: "전월 광고매출",
  roas_previous: "전월 ROAS",
  revenue_change: "매출 증감",
  orders_change: "주문 증감",
  units_change: "판매량 증감",
  ad_spend_change: "광고비 증감",
  ad_revenue_change: "광고매출 증감",
  roas_change_pp: "ROAS 증감",
  visits: "방문수",
  gross_revenue: "총매출",
  aov: "결제단가",
  conversion_rate: "구매전환율",
  refund_rate: "환불률",
  discount_rate: "할인율",
  visits_previous: "전월 방문수",
  gross_revenue_previous: "전월 총매출",
  aov_previous: "전월 결제단가",
  conversion_rate_previous: "전월 구매전환율",
  refund_rate_previous: "전월 환불률",
  discount_rate_previous: "전월 할인율",
  visits_change: "방문수 증감",
  gross_revenue_change: "총매출 증감",
  aov_change: "결제단가 증감",
  conversion_rate_change_pp: "구매전환율 증감",
  refund_rate_change_pp: "환불률 증감",
  discount_rate_change_pp: "할인율 증감",
};

const WON_KEYS = new Set(
  ["revenue", "ad_spend", "ad_revenue", "gross_revenue", "aov"].flatMap((k) => [k, `${k}_previous`]),
);
const PERCENT_KEYS = new Set(
  ["roas", "conversion_rate", "refund_rate", "discount_rate"].flatMap((k) => [k, `${k}_previous`]),
);

function formatCell(key: string, v: unknown): string {
  if (v === null || v === undefined) return "-";
  if (key === "platform") return platformLabel(String(v));
  if (typeof v !== "number") return String(v);
  if (PERCENT_KEYS.has(key)) return `${v.toFixed(1)}%`;
  if (key.endsWith("_change_pp")) return `${v > 0 ? "+" : ""}${v.toFixed(1)}%p`;
  if (key.endsWith("_change")) return `${v > 0 ? "+" : ""}${v.toFixed(1)}%`;
  if (WON_KEYS.has(key)) return `${Math.round(v).toLocaleString("ko-KR")}원`;
  return v.toLocaleString("ko-KR");
}

function AnswerTable({ rows }: { rows: Record<string, unknown>[] }) {
  const isDiagnosis = rows.every((r) => r.diagnosis === "opportunity" || r.diagnosis === "attention");
  const cols = isDiagnosis
    ? ["rank", "product_name", "platform", "score", "evaluated_rules", "data_scope",
        "revenue_change", "orders_change", "units_change", "roas", "roas_change_pp",
        "ad_spend_change", "ad_revenue_change", "conversion_rate_change_pp", "refund_rate_change_pp"]
        .filter((key) => rows.some((r) => r[key] !== null && r[key] !== undefined))
    : Object.keys(rows[0]);
  return (
    <div className="table-wrap answer">
      <table>
        <thead>
          <tr>
            {cols.map((c) => (
              <th key={c}>{COLUMN_LABEL[c] ?? c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {cols.map((c) => (
                <td key={c}>{formatCell(c, r[c])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function List({ title, items, tone }: { title: string; items?: string[]; tone: string }) {
  if (!items?.length) return null;
  return (
    <div className="insight-block">
      <span className={`insight-title ${tone}`}>{title}</span>
      <ul>
        {items.map((it) => (
          <li key={it}>{it}</li>
        ))}
      </ul>
    </div>
  );
}

export function InsightBody({ insight, onRetry }: { insight: Insight; onRetry?: () => void }) {
  if (insight.status === "llm_error") {
    return (
      <div className="notice error">
        AI 분석을 불러오지 못했습니다. KPI 결과는 정상입니다.
        {onRetry && (
          <button className="link" onClick={onRetry}>
            다시 시도
          </button>
        )}
      </div>
    );
  }
  if (insight.status === "unsupported_question") {
    return (
      <div className="notice">
        {/* 백엔드가 이유(없는 월, 필요한 파일, 계산 결과 모순 등)를 주면 그대로 보여준다 */}
        {insight.summary || "이 질문은 현재 데이터로 분석하기 어렵습니다."} 예시:{" "}
        {EXAMPLE_QUESTIONS.map((e) => `“${e}”`).join(", ")}
        {insight.limitations?.map((l) => (
          <p key={l} className="muted small">
            ※ {l}
          </p>
        ))}
      </div>
    );
  }
  if (insight.status === "skipped") return null;

  return (
    <div className="insight">
      {insight.summary && <p className="insight-summary">{insight.summary}</p>}
      {insight.answer && insight.answer.length > 0 && <AnswerTable rows={insight.answer} />}
      <List title="근거" items={insight.evidence} tone="gray" />
      <List title="확인 항목" items={insight.checks} tone="blue" />
      <List title="행동 제안" items={insight.actions} tone="green" />
      {insight.limitations?.map((l) => (
        <p key={l} className="muted small">
          ※ {l}
        </p>
      ))}
    </div>
  );
}
