"use client";

import { useRef, useState } from "react";
import type { PreviewFile } from "@/types/api";
import { formatBytes, platformLabel } from "@/lib/format";

interface Props {
  files: File[];
  previews: PreviewFile[];
  busy: boolean;
  checking: boolean;
  periodInputs: Record<string, string>;
  missingPeriods: number;
  onPeriodChange: (filename: string, period: string) => void;
  onFilesChange: (files: File[]) => void;
  onAnalyze: () => void;
  /** 결과 전 랜딩 화면에서는 큰 업로드 카드로 보여준다. */
  hero?: boolean;
}

export function UploadPanel({
  files,
  previews,
  busy,
  checking,
  periodInputs,
  missingPeriods,
  onPeriodChange,
  onFilesChange,
  onAnalyze,
  hero = false,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [openPreview, setOpenPreview] = useState<string | null>(null);

  const addFiles = (list: FileList | null) => {
    if (!list) return;
    const names = new Set(files.map((f) => f.name));
    onFilesChange([...files, ...Array.from(list).filter((f) => !names.has(f.name))]);
  };

  const removeFile = (name: string) => onFilesChange(files.filter((f) => f.name !== name));
  const previewFor = (name: string) => previews.find((p) => p.filename === name);
  const opened = openPreview ? previewFor(openPreview) : undefined;

  return (
    <section className={`card upload${hero ? " is-hero" : ""}`}>
      <div
        className={`dropzone${dragOver ? " is-over" : ""}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          addFiles(e.dataTransfer.files);
        }}
      >
        <span className="dz-icon" aria-hidden>↑</span>
        <strong className="dz-title">Drag &amp; drop files</strong>
        <span className="muted">Excel(.xlsx), CSV · 최대 10개 · 파일당 5MB</span>
        <span className="btn primary dz-btn">파일 선택하기</span>
        <span className="dz-platforms">
          <span className="muted small">지원</span>
          {[
            ["쿠팡", "coupang"],
            ["네이버", "naver"],
            ["판매 리포트", ""],
            ["광고 리포트", ""],
          ].map(([label, tone]) => (
            <span key={label} className={`dz-chip ${tone}`}>
              {label}
            </span>
          ))}
        </span>
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.csv"
          multiple
          hidden
          onChange={(e) => {
            addFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {files.length > 0 && (
        <>
          <ul className="file-list">
            {files.map((f) => {
              const p = previewFor(f.name);
              return (
                <li key={f.name}>
                  <span className="file-name">{f.name}</span>
                  <span className="muted small">{formatBytes(f.size)}</span>
                  {p ? (
                    <span className="muted">
                      {platformLabel(p.platform)} · {p.periods.length ? `${p.periods.join(", ")} · ` : ""}
                      {p.row_count}행
                    </span>
                  ) : (
                    <span className="muted">{checking ? "확인 중..." : "확인 실패"}</span>
                  )}
                  {p && p.periods.length === 0 && (
                    <label className={`period-input${periodInputs[f.name] ? "" : " is-missing"}`}>
                      <span className="small">기간 정보 없음 · 월 선택</span>
                      <input
                        type="month"
                        value={periodInputs[f.name] ?? ""}
                        onChange={(e) => onPeriodChange(f.name, e.target.value)}
                        disabled={busy}
                        aria-label={`${f.name} 기간(월)`}
                      />
                    </label>
                  )}
                  <span className="file-actions">
                    {p && (
                      <button className="link" onClick={() => setOpenPreview(openPreview === f.name ? null : f.name)}>
                        {openPreview === f.name ? "닫기" : "미리보기"}
                      </button>
                    )}
                    <button className="link danger" onClick={() => removeFile(f.name)} disabled={busy}>
                      삭제
                    </button>
                  </span>
                </li>
              );
            })}
          </ul>

          {opened && (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    {opened.columns.map((c) => (
                      <th key={c}>{c}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {opened.preview.map((row, i) => (
                    <tr key={i}>
                      {opened.columns.map((c) => (
                        <td key={c}>{typeof row[c] === "number" ? row[c]!.toLocaleString("ko-KR") : row[c] ?? ""}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {missingPeriods > 0 && (
            <p className="notice warn small">
              기간 정보가 없는 파일 {missingPeriods}개가 있어요. 각 파일의 월을 선택해야 분석을 시작할 수 있습니다.
            </p>
          )}
          <button className="btn primary" onClick={onAnalyze} disabled={busy || missingPeriods > 0}>
            {busy ? "분석 중..." : "분석 시작"}
          </button>
        </>
      )}
    </section>
  );
}
