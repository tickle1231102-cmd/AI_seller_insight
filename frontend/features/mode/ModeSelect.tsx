import type { AnalysisMode } from "./mode";

const OPTIONS: { mode: AnalysisMode; title: string; desc: string }[] = [
  { mode: "sales", title: "매출 분석", desc: "매출 · 주문 · 판매량 중심으로 봅니다" },
  { mode: "ad", title: "광고 분석", desc: "광고비 · 광고매출 · ROAS 중심으로 봅니다" },
];

export function ModeSelect({ onSelect }: { onSelect: (mode: AnalysisMode) => void }) {
  return (
    <section className="card mode-select">
      <h2>어떤 분석을 볼까요?</h2>
      <p className="muted small">분석은 끝났어요. 언제든 상단 토글로 바꿀 수 있어요.</p>
      <div className="mode-options">
        {OPTIONS.map((o) => (
          <button key={o.mode} type="button" className="mode-option" onClick={() => onSelect(o.mode)}>
            <strong>{o.title}</strong>
            <span className="muted small">{o.desc}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
