"use client";

import { useEffect, useId, useRef, useState, type ReactNode } from "react";

export function FloatingChat({ children, pending, stale }: { children: ReactNode; pending: boolean; stale: boolean }) {
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
  return <>
    <button ref={trigger} className="ai-summary-fab ai-chat-fab" type="button"
      aria-haspopup="dialog" aria-controls={id} aria-expanded={open}
      onClick={() => { dialog.current?.showModal(); setOpen(true); }}>
      <svg className="ai-summary-sparkle" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M20 11a8 8 0 0 1-8 8H5l-3 3V11a9 9 0 0 1 18 0Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round"/><path d="M7 10h8M7 14h5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"/></svg>
      <span><strong>AI 물어보기</strong><small aria-live="polite">{pending ? "답변 작성 중 · 닫아도 계속돼요" : "내 데이터로 궁금한 점 질문하기"}</small></span>
    </button>
    <dialog ref={dialog} id={id} className="ai-summary-dialog ai-chat-dialog" aria-labelledby={`${id}-title`}
      onClose={() => { setOpen(false); trigger.current?.focus({ preventScroll: true }); }}
      onKeyDown={(event) => {
        if (event.key !== "Tab") return;
        const controls = Array.from(event.currentTarget.querySelectorAll<HTMLElement>("button:not(:disabled), a[href], input:not(:disabled), [tabindex='0']")).filter(el => el.getClientRects().length > 0);
        const first = controls[0], last = controls[controls.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
      }}
      onClick={(event) => {
        if (event.target !== event.currentTarget) return;
        const r = event.currentTarget.getBoundingClientRect();
        if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) dialog.current?.close();
      }}>
      <div className="ai-summary-shell">
        <header className="ai-summary-header"><div><span className="ai-summary-eyebrow">SELLER INSIGHT</span><h2 id={`${id}-title`}>AI 물어보기</h2></div>
          <button className="ai-summary-close" type="button" aria-label="AI 물어보기 닫기" onClick={() => dialog.current?.close()}>✕</button>
        </header>
        <p className="muted small">마지막으로 분석한 자료에 대해 질문해 보세요. 창을 닫아도 대화는 유지됩니다.</p>
        {stale && <p className="notice warn">파일이나 월이 바뀌었어요. 답변은 이전 분석 기준입니다. 새 자료는 다시 분석해 주세요.</p>}
        {children}
      </div>
    </dialog>
  </>;
}
