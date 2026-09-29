"use client";

import { useRef, useState } from "react";
import type { AnalyzeResponse, PreviewFile } from "@/types/api";
import { analyzeFiles, ApiRequestError, previewFiles, USE_MOCK, validateFiles } from "@/lib/api/client";
import { platformLabel } from "@/lib/format";
import { UploadPanel } from "@/features/upload/UploadPanel";
import { KpiCards } from "@/features/dashboard/KpiCards";
import { TrendChart } from "@/features/dashboard/TrendChart";
import { PlatformCompare } from "@/features/dashboard/PlatformCompare";
import { StoreSection } from "@/features/dashboard/StoreSection";
import { SignalBadges } from "@/features/dashboard/SignalBadges";
import { InsightPanel } from "@/features/insight/InsightPanel";
import { ChatPanel, type ChatMessage } from "@/features/insight/ChatPanel";

type Status = "idle" | "uploading" | "analyzing" | "done" | "error";

const errorMessage = (e: unknown) =>
  e instanceof ApiRequestError ? e.message : "알 수 없는 오류가 발생했습니다.";

export default function Home() {
  const [files, setFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<PreviewFile[]>([]);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatPending, setChatPending] = useState(false);
  const nextId = useRef(0);

  const handleFilesChange = async (next: File[]) => {
    setFiles(next);
    setError(null);
    if (next.length === 0) {
      setPreviews([]);
      setStatus("idle");
      return;
    }
    const invalid = validateFiles(next);
    if (invalid) {
      setError(invalid);
      setStatus("error");
      return;
    }
    setStatus("uploading");
    try {
      const res = await previewFiles(next);
      setPreviews(res.files);
      setStatus(result ? "done" : "idle");
    } catch (e) {
      setError(errorMessage(e));
      setStatus("error");
    }
  };

  const runAnalyze = async () => {
    const invalid = validateFiles(files);
    if (invalid) {
      setError(invalid);
      setStatus("error");
      return;
    }
    setError(null);
    setStatus("analyzing");
    try {
      setResult(await analyzeFiles(files));
      setStatus("done");
    } catch (e) {
      setError(errorMessage(e));
      setStatus("error");
    }
  };

  const sendQuestion = async (question: string) => {
    setMessages((m) => [...m, { id: nextId.current++, role: "user", text: question }]);
    setChatPending(true);
    try {
      const res = await analyzeFiles(files, question);
      setMessages((m) => [...m, { id: nextId.current++, role: "ai", insight: res.insight }]);
    } catch (e) {
      setMessages((m) => [...m, { id: nextId.current++, role: "error", text: errorMessage(e) }]);
    } finally {
      setChatPending(false);
    }
  };

  const busy = status === "uploading" || status === "analyzing";
  const periodLabel = result
    ? result.kpis.previous_period
      ? `${result.kpis.previous_period} vs ${result.kpis.period}`
      : result.kpis.period
    : null;

  return (
    <main className="page">
      <header className="header">
        <div>
          <h1>Seller Insight AI</h1>
          <p className="muted">멀티플랫폼 판매·광고 성과 대시보드</p>
        </div>
        {USE_MOCK && <span className="badge">Mock 데이터 모드</span>}
      </header>

      <UploadPanel
        files={files}
        previews={previews}
        busy={busy}
        onFilesChange={handleFilesChange}
        onAnalyze={runAnalyze}
      />

      {error && (
        <div className="notice error" role="alert">
          {error}
        </div>
      )}

      {status === "analyzing" && !result && (
        <div className="loading">
          <div className="spinner" />
          데이터를 분석하고 있습니다...
        </div>
      )}

      {result && (
        <div className={`results${status === "analyzing" ? " is-stale" : ""}`}>
          <div className="filter-row card">
            <span className="chip">전체 플랫폼</span>
            {result.comparison.by_platform.map((p) => (
              <span key={p.platform} className="chip">
                {platformLabel(p.platform)}
              </span>
            ))}
            <span className="grow" />
            {periodLabel && <span className="chip">{periodLabel}</span>}
            <span className="muted small">업로드 파일 {files.length}개</span>
          </div>

          <KpiCards kpis={result.kpis} />
          <SignalBadges signals={result.signals} />
          {result.store && <StoreSection store={result.store} />}

          <div className="main-row">
            <div className="left-col">
              <TrendChart trend={result.comparison.trend} />
              <PlatformCompare data={result.comparison.by_platform} />
            </div>
            <InsightPanel insight={result.insight} onRetry={runAnalyze} />
          </div>
        </div>
      )}

      <ChatPanel
        messages={messages}
        pending={chatPending}
        disabled={!result}
        onSend={sendQuestion}
        onReset={() => setMessages([])}
      />
    </main>
  );
}
