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
import { DashboardViewToggle, PlatformDashboard, type DashboardView } from "@/features/dashboard/PlatformDashboard";
import { label as dashboardPlatformLabel } from "@/features/dashboard/dashboardMetrics";
import { SignalBadges } from "@/features/dashboard/SignalBadges";
import { InsightPanel } from "@/features/insight/InsightPanel";
import { ChatPanel, type ChatMessage } from "@/features/insight/ChatPanel";
import { ModeSelect } from "@/features/mode/ModeSelect";
import { ModeToggle } from "@/features/mode/ModeToggle";
import type { AnalysisMode } from "@/features/mode/mode";

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
  // 분석 유형은 첫 분석 결과가 나온 뒤 고른다. 표시만 바꾸므로 바꿔도 API 를 다시 부르지 않는다 (#29).
  const [mode, setMode] = useState<AnalysisMode | null>(null);
  const [dashboardView, setDashboardView] = useState<DashboardView>("simple");
  const [collapsedPlatforms, setCollapsedPlatforms] = useState<Record<string, boolean>>({});
  // 마지막으로 성공한 분석의 입력. 파일·월을 바꿔도 화면 결과와 질문이 같은 기준을 쓰도록 질문은 이 스냅샷으로 보낸다.
  const [analyzed, setAnalyzed] = useState<{ files: File[]; periods: Record<string, string> } | null>(null);
  const nextId = useRef(0);
  // 늦게 도착한 이전 분석·질문 응답이 새 결과를 덮지 않도록 분석마다 올린다.
  const analyzeSeq = useRef(0);

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
    const seq = ++analyzeSeq.current;
    // 진행 중이던 질문의 답은 버려지므로 대기 상태도 함께 푼다.
    setChatPending(false);
    const snapshot = { files, periods: periodInputs };
    try {
      const res = await analyzeFiles(snapshot.files, undefined, snapshot.periods);
      if (seq !== analyzeSeq.current) return;
      setResult(res);
      setCollapsedPlatforms({});
      // 파일 구성이 바뀌면 이전 모드가 맞지 않을 수 있어 다시 고르게 한다. 같은 파일 재시도는 모드를 유지한다.
      if (analyzed && snapshot.files !== analyzed.files) setMode(null);
      setAnalyzed(snapshot);
      // 분석 기준이 바뀌었으므로 이전 기준의 대화는 비운다.
      setMessages([]);
      setStatus("done");
    } catch (e) {
      if (seq !== analyzeSeq.current) return;
      setError(errorMessage(e));
      setStatus("error");
    }
  };

  const sendQuestion = async (question: string) => {
    // 재분석 중에는 analyzed 가 아직 이전 기준이라, 답이 새 결과 뒤에 붙지 않도록 질문을 막는다.
    if (!analyzed || status === "analyzing") return;
    const seq = analyzeSeq.current;
    setMessages((m) => [...m, { id: nextId.current++, role: "user", text: question }]);
    setChatPending(true);
    try {
      const res = await analyzeFiles(analyzed.files, question, analyzed.periods);
      if (seq !== analyzeSeq.current) return;
      setMessages((m) => [...m, { id: nextId.current++, role: "ai", insight: res.insight }]);
    } catch (e) {
      if (seq !== analyzeSeq.current) return;
      setMessages((m) => [...m, { id: nextId.current++, role: "error", text: errorMessage(e) }]);
    } finally {
      if (seq === analyzeSeq.current) setChatPending(false);
    }
  };

  // 분석 뒤에 파일이나 월 입력을 바꿨는지. 화면 결과·질문은 마지막 분석 기준 그대로다.
  const inputsChanged = !!analyzed && (files !== analyzed.files || periodInputs !== analyzed.periods);
  const busy = status === "uploading" || status === "analyzing";
  const periodLabel = result
    ? result.kpis.previous_period
      ? `${result.kpis.previous_period} vs ${result.kpis.period}`
      : result.kpis.period
    : null;
  // 광고 리포트 없이 스마트스토어만 올린 경우. 광고비 0 은 정상 광고 데이터에도 있어 플랫폼으로 판단한다.
  const storeOnly =
    !!result &&
    result.comparison.by_platform.length > 0 &&
    result.comparison.by_platform.every((p) => p.platform === "naver_store");

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

      {result && inputsChanged && status !== "analyzing" && (
        <div className="notice warn">
          파일이나 월을 바꿨어요. 아래 결과와 AI 답변은 이전 분석 기준이에요. 다시 분석하면 새 기준으로 바뀌어요.
        </div>
      )}

      {result && !mode && <ModeSelect onSelect={setMode} />}

      {result && mode && (
        <div className={`results${status === "analyzing" ? " is-stale" : ""}`}>
          <div className="filter-row card">
            <span className="chip">전체 플랫폼</span>
            {result.dashboard ? result.dashboard.platforms.map((p) => <span key={p.platform} className="chip">{dashboardPlatformLabel(p)}</span>) : result.comparison.by_platform.map((p) => (
              <span key={p.platform} className="chip">
                {platformLabel(p.platform)}
              </span>
            ))}
            <span className="grow" />
            <ModeToggle mode={mode} onChange={setMode} />
            {result.dashboard && <DashboardViewToggle value={dashboardView} onChange={setDashboardView} />}
            {periodLabel && <span className="chip">{periodLabel}</span>}
            <span className="muted small">분석한 파일 {analyzed?.files.length ?? files.length}개</span>
          </div>

          {!result.dashboard && mode === "ad" && storeOnly && (
            <div className="notice warn">
              광고 리포트가 없어요. 쿠팡·네이버 광고 파일을 함께 올리거나 매출 분석으로 전환해 주세요.
            </div>
          )}
          {result.dashboard ? <PlatformDashboard data={result.dashboard} view={dashboardView} mode={mode} collapsed={collapsedPlatforms} onToggle={(p) => setCollapsedPlatforms((prev) => ({ ...prev, [p]: !prev[p] }))} /> : <KpiCards kpis={result.kpis} mode={mode} />}
          <SignalBadges signals={result.signals} />
          {!result.dashboard && mode === "sales" && result.store && <StoreSection store={result.store} />}

          <p className="muted small">AI는 선택한 화면 모드와 무관하게 업로드된 전체 데이터 기준으로 답합니다.</p>
          <div className={result.dashboard ? "" : "main-row"}>
            {!result.dashboard && (
            <div className="left-col">
              {!(mode === "ad" && storeOnly) && (
                <>
                  <TrendChart trend={result.comparison.trend} mode={mode} />
                  <PlatformCompare data={result.comparison.by_platform} mode={mode} />
                </>
              )}
              {!result.dashboard && mode === "ad" && result.store && <StoreSection store={result.store} />}
            </div>
            )}
            <InsightPanel insight={result.insight} onRetry={runAnalyze} />
          </div>
        </div>
      )}

      <ChatPanel
        messages={messages}
        pending={chatPending}
        disabled={!result || !mode || status === "analyzing"}
        disabledReason={
          status === "analyzing"
            ? "분석 중이에요. 분석이 끝나면 질문할 수 있어요."
            : result && !mode
              ? "분석 유형을 고르면 질문할 수 있어요."
              : undefined
        }
        onSend={sendQuestion}
        onReset={() => setMessages([])}
      />
    </main>
  );
}
