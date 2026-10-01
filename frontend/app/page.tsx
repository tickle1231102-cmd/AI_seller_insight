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
import { CoupangSection } from "@/features/dashboard/CoupangSection";
import { SignalBadges } from "@/features/dashboard/SignalBadges";
import { InsightPanel } from "@/features/insight/InsightPanel";
import { ChatPanel, type ChatMessage } from "@/features/insight/ChatPanel";

type Status = "idle" | "uploading" | "analyzing" | "done" | "error";

const errorMessage = (e: unknown) =>
  e instanceof ApiRequestError ? e.message : "알 수 없는 오류가 발생했습니다.";

export default function Home() {
  const [files, setFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<PreviewFile[]>([]);
  // 파일에 기간 정보가 없어(미리보기 periods 가 빈 배열) 사용자가 고른 월 { 파일명: "YYYY-MM" }
  const [periodInputs, setPeriodInputs] = useState<Record<string, string>>({});
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatPending, setChatPending] = useState(false);
  const nextId = useRef(0);

  const handleFilesChange = async (next: File[]) => {
    setError(null);
    if (next.length === 0) {
      setFiles(next);
      setPreviews([]);
      setPeriodInputs({});
      setStatus("idle");
      return;
    }
    const invalid = validateFiles(next);
    if (invalid) {
      // 개수·크기·확장자 오류면 새 파일을 목록에 넣지 않고 기존 목록을 유지한다.
      setError(invalid);
      setStatus("error");
      return;
    }
    setFiles(next);
    setStatus("uploading");
    try {
      const res = await previewFiles(next);
      setPreviews(res.files);
      // 목록에서 빠진 파일의 입력값은 버린다
      setPeriodInputs((prev) =>
        Object.fromEntries(Object.entries(prev).filter(([name]) => next.some((f) => f.name === name))),
      );
      setStatus(result ? "done" : "idle");
    } catch (e) {
      setError(errorMessage(e));
      setStatus("error");
    }
  };

  const missingPeriods = previews.filter((p) => p.periods.length === 0 && !periodInputs[p.filename]);

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
      setResult(await analyzeFiles(files, undefined, periodInputs));
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
      const res = await analyzeFiles(files, question, periodInputs);
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
        checking={status === "uploading"}
        periodInputs={periodInputs}
        missingPeriods={missingPeriods.length}
        onPeriodChange={(name, period) => setPeriodInputs((prev) => ({ ...prev, [name]: period }))}
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
          {result.coupang && <CoupangSection coupang={result.coupang} />}

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
