"use client";

import { useEffect, useId, useRef, useState } from "react";
import type { Insight } from "@/types/api";
import { InsightBody } from "./InsightBody";

export function FloatingInsight({ insight, period, busy, stale, onRetry }: {
  insight: Insight; period: string; busy: boolean; stale: boolean; onRetry: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const [open, setOpen] = useState(false);
  const id = useId();

  useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = previous; };
  }, [open]);

  function show() {
    dialog.current?.showModal();
    setOpen(true);
  }
  function close() { dialog.current?.close(); }

  return <>
    <button ref={trigger} type="button" className="ai-summary-fab" onClick={show}
      aria-haspopup="dialog" aria-controls={id} aria-expanded={open}>
      <svg className="ai-summary-sparkle" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="m12 3 2.3 6.7L21 12l-6.7 2.3L12 21l-2.3-6.7L3 12l6.7-2.3L12 3Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
        <path d="M20 2v4M18 4h4" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      </svg>
      <span><strong>AI 분석 요약하기</strong><small>{busy ? "분석 결과 업데이트 중" : "핵심 요약 · 근거 한눈에"}</small></span>
      <svg className="ai-summary-arrow" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m9 5 7 7-7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
    </button>
    <dialog ref={dialog} id={id} className="ai-summary-dialog" aria-labelledby={`${id}-title`} aria-describedby={`${id}-description`}
      onClose={() => { setOpen(false); trigger.current?.focus({ preventScroll: true }); }}
      onKeyDown={(event) => {
        if (event.key !== "Tab") return;
        const controls = Array.from(event.currentTarget.querySelectorAll<HTMLElement>("button:not(:disabled), a[href], input:not(:disabled), [tabindex='0']"))
          .filter((element) => element.getClientRects().length > 0);
        const first = controls[0], last = controls[controls.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
      }}
      onClick={(event) => {
        if (event.target !== event.currentTarget) return;
        const rect = event.currentTarget.getBoundingClientRect();
        if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) close();
      }}>
      <div className="ai-summary-shell">
        <header className="ai-summary-header">
          <div><span className="ai-summary-eyebrow">SELLER INSIGHT</span><h2 id={`${id}-title`}>AI 분석 요약</h2></div>
          <button type="button" className="ai-summary-close" onClick={close} aria-label="AI 분석 요약 닫기">
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" /></svg>
          </button>
        </header>
        <p id={`${id}-description`} className="muted small">{period} · 마지막으로 분석한 업로드 자료 기준입니다. 열고 닫아도 추가 분석을 요청하지 않습니다.</p>
        {stale && <p className="notice warn">파일이나 월이 바뀌었어요. 아래 요약은 이전 분석 기준입니다. 창을 닫고 다시 분석해 주세요.</p>}
        <div className="ai-summary-content" aria-busy={busy}>
          {busy ? <p className="notice" role="status">분석 결과를 업데이트하고 있습니다.</p> : insight.status === "skipped" ?
            <p className="notice">이번 분석에는 AI 요약이 제공되지 않았습니다. 대시보드에서 수치를 확인할 수 있어요.</p> :
            <InsightBody insight={insight} onRetry={stale ? undefined : onRetry} />}
        </div>
        <footer className="ai-summary-footer"><span className="muted small">실행 전 원자료와 근거를 확인하세요.</span><button type="button" className="btn secondary" onClick={close}>대시보드로 돌아가기</button></footer>
      </div>
    </dialog>
  </>;
}
