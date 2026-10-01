import type { Insight } from "@/types/api";

import { platformLabel } from "@/lib/format";

// 질문 범위 확대에 맞춰 유형별(순위·비교·필터·진단) 예시를 둔다.
// 확장 유형은 백엔드 Planner 반영 전까지 unsupported_question 이 올 수 있다.
export const EXAMPLE_QUESTIONS = [
  "광고 효율이 가장 안 좋은 플랫폼 어디야?",
  "이번 달 매출이 가장 높은 상품은?",
  "전월 대비 매출이 가장 많이 떨어진 상품은?",
  "쿠팡에서 광고비랑 광고매출 같이 보여줘",
  "이번 달 매출이 줄어든 원인 후보는?",
];

const SUPPORTED_SCOPE = [
  "지표 순위 (매출·주문·광고비·ROAS 등)",
  "전월 대비 비교",
  "플랫폼·상품 조건",
  "원인 후보 진단",
];

const COLUMN_LABEL: Record<string, string> = {
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
  const cols = Object.keys(rows[0]);
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
        <p>{insight.summary || "이 질문은 현재 데이터로 분석하기 어렵습니다."}</p>
        <p className="small">이런 질문을 할 수 있어요: {SUPPORTED_SCOPE.join(" · ")}</p>
        <p className="small">예시: {EXAMPLE_QUESTIONS.map((e) => `“${e}”`).join(", ")}</p>
        {insight.limitations?.map((l) => (
          <p key={l} className="muted small">
            ※ {l}
          </p>
        ))}
      </div>
    );
  }
  if (insight.status === "skipped") return null;

  // 진단형 질문은 answer 표 없이 설명만 올 수 있다. 내용이 하나도 없으면 빈 카드 대신 안내한다.
  const hasContent =
    !!insight.summary ||
    !!insight.answer?.length ||
    [insight.evidence, insight.checks, insight.actions, insight.limitations].some((l) => l?.length);
  if (!hasContent) {
    return <div className="notice">분석 결과가 비어 있습니다. 질문을 조금 더 구체적으로 입력해보세요.</div>;
  }

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
