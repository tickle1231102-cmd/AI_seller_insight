"use client";

import { useRef, useState } from "react";
import type { PreviewFile } from "@/types/api";
import { formatBytes, platformLabel } from "@/lib/format";

interface Props {
  files: File[];
  previews: PreviewFile[];
  busy: boolean;
  checking: boolean;
  onFilesChange: (files: File[]) => void;
  onAnalyze: () => void;
}

export function UploadPanel({ files, previews, busy, checking, onFilesChange, onAnalyze }: Props) {
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
    <section className="card upload">
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
        <strong>Excel / CSV 파일을 끌어다 놓거나 클릭해서 선택</strong>
        <span className="muted">쿠팡·네이버 판매·광고 리포트 · 최대 10개 · 파일당 5MB</span>
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
                      {platformLabel(p.platform)} · {p.periods.join(", ")} · {p.row_count}행
                    </span>
                  ) : (
                    <span className="muted">{checking ? "확인 중..." : "확인 실패"}</span>
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

          <button className="btn primary" onClick={onAnalyze} disabled={busy}>
            {busy ? "분석 중..." : "분석 시작"}
          </button>
        </>
      )}
    </section>
  );
}
