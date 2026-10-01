import { MODE_LABEL, type AnalysisMode } from "./mode";

export function ModeToggle({ mode, onChange }: { mode: AnalysisMode; onChange: (mode: AnalysisMode) => void }) {
  return (
    <div className="mode-toggle" role="radiogroup" aria-label="분석 유형">
      {(Object.keys(MODE_LABEL) as AnalysisMode[]).map((m) => (
        <button
          key={m}
          type="button"
          role="radio"
          aria-checked={mode === m}
          className={mode === m ? "is-active" : ""}
          onClick={() => onChange(m)}
        >
          {MODE_LABEL[m]}
        </button>
      ))}
    </div>
  );
}
