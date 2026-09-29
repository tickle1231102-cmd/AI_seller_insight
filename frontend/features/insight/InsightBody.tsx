import type { Insight } from "@/types/api";

import { platformLabel } from "@/lib/format";

export const EXAMPLE_QUESTIONS = [
  "광고 효율이 가장 안 좋은 플랫폼 어디야?",
  "이번 달 매출이 가장 높은 상품은?",
  "광고비가 가장 많이 늘어난 플랫폼은?",
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
};

function formatCell(key: string, v: unknown): string {
  if (v === null || v === undefined) return "-";
  if (key === "platform") return platformLabel(String(v));
  if (typeof v !== "number") return String(v);
  if (key === "roas") return `${v.toFixed(1)}%`;
  if (key === "revenue" || key === "ad_spend" || key === "ad_revenue") return `${Math.round(v).toLocaleString("ko-KR")}원`;
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
        이 질문은 현재 데이터로 분석하기 어렵습니다. 예시: {EXAMPLE_QUESTIONS.map((e) => `“${e}”`).join(", ")}
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
