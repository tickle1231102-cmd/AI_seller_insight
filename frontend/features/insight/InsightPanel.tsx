import type { Insight } from "@/types/api";
import { InsightBody } from "./InsightBody";

export function InsightPanel({ insight, onRetry }: { insight: Insight; onRetry: () => void }) {
  return (
    <aside className="card insight-panel">
      <span className="tag">AI 분석 요약</span>
      <InsightBody insight={insight} onRetry={onRetry} />
    </aside>
  );
}
