import type { Insight } from "@/types/api";

const EXAMPLES = ["광고 효율이 가장 안 좋은 플랫폼 어디야?", "이번 달 매출이 가장 높은 상품은?"];

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
        이 질문은 현재 데이터로 분석하기 어렵습니다. 예시: {EXAMPLES.map((e) => `“${e}”`).join(", ")}
      </div>
    );
  }
  if (insight.status === "skipped") return null;

  return (
    <div className="insight">
      {insight.summary && <p className="insight-summary">{insight.summary}</p>}
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
