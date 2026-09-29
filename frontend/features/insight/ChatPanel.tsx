"use client";

import { useEffect, useRef, useState } from "react";
import type { Insight } from "@/types/api";
import { MAX_QUESTION_LENGTH } from "@/lib/api/client";
import { EXAMPLE_QUESTIONS, InsightBody } from "./InsightBody";

export type ChatMessage =
  | { id: number; role: "user"; text: string }
  | { id: number; role: "ai"; insight: Insight }
  | { id: number; role: "error"; text: string };

interface Props {
  messages: ChatMessage[];
  pending: boolean;
  disabled: boolean;
  onSend: (question: string) => void;
  onReset: () => void;
}

export function ChatPanel({ messages, pending, disabled, onSend, onReset }: Props) {
  const [text, setText] = useState("");
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, pending]);

  const submit = () => {
    const q = text.trim();
    if (!q || pending || disabled || q.length > MAX_QUESTION_LENGTH) return;
    onSend(q);
    setText("");
  };

  return (
    <section className="card chat">
      <header className="chat-header">
        <span className="dot" />
        <h2>AI 어시스턴트와 대화하기</h2>
        <button className="link" onClick={onReset} disabled={messages.length === 0 || pending}>
          대화 초기화
        </button>
      </header>

      <div className="chat-list" ref={listRef}>
        {messages.length === 0 && (
          <p className="muted small center">
            {disabled ? "파일을 업로드하고 분석을 시작하면 질문할 수 있습니다." : "판매·광고 데이터에 대해 무엇이든 물어보세요."}
          </p>
        )}
        {messages.map((m) =>
          m.role === "user" ? (
            <div key={m.id} className="bubble-row right">
              <div className="bubble user">{m.text}</div>
            </div>
          ) : m.role === "ai" ? (
            <div key={m.id} className="bubble-row">
              <div className="bubble ai">
                <InsightBody insight={m.insight} />
              </div>
            </div>
          ) : (
            <div key={m.id} className="bubble-row">
              <div className="bubble ai error-text">{m.text}</div>
            </div>
          ),
        )}
        {pending && (
          <div className="bubble-row">
            <div className="bubble ai typing" aria-label="AI 응답 생성 중">
              <span />
              <span />
              <span />
            </div>
          </div>
        )}
      </div>

      {!disabled && (
        <div className="examples">
          {EXAMPLE_QUESTIONS.map((q) => (
            <button key={q} className="chip-btn" onClick={() => onSend(q)} disabled={pending}>
              {q}
            </button>
          ))}
        </div>
      )}

      <form
        className="chat-input"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="판매·광고 데이터에 대해 질문해보세요..."
          maxLength={MAX_QUESTION_LENGTH}
          disabled={disabled}
        />
        <span className="muted small counter">
          {text.length}/{MAX_QUESTION_LENGTH}
        </span>
        <button className="btn primary" type="submit" disabled={disabled || pending || !text.trim()}>
          전송
        </button>
      </form>
    </section>
  );
}
