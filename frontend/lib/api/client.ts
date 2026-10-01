import type { AnalyzeResponse, ApiError, PreviewResponse } from "@/types/api";
import { mockAnalyze, mockPreview } from "./mock";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;
export const USE_MOCK = !BASE_URL || process.env.NEXT_PUBLIC_USE_MOCK === "true";

export const MAX_FILES = 10;
export const MAX_FILE_SIZE = 5 * 1024 * 1024;
export const MAX_QUESTION_LENGTH = 300;
export const ALLOWED_EXTENSIONS = [".xlsx", ".csv"];

export class ApiRequestError extends Error {
  constructor(public code: string, message: string, public details?: Record<string, unknown>) {
    super(message);
  }
}

const MESSAGES: Record<string, (d?: Record<string, unknown>) => string> = {
  NO_FILES: () => "업로드할 파일을 선택해주세요.",
  TOO_MANY_FILES: () => `파일은 최대 ${MAX_FILES}개까지 업로드할 수 있습니다.`,
  FILE_TOO_LARGE: (d) => `${d?.file ? `${d.file}: ` : ""}파일 크기는 5MB 이하여야 합니다.`,
  UNSUPPORTED_FILE_TYPE: (d) => `${d?.file ? `${d.file}: ` : ""}.xlsx 또는 .csv 파일만 업로드할 수 있습니다.`,
  EMPTY_FILE: (d) => `${d?.file ? `${d.file}: ` : ""}데이터가 없는 파일입니다.`,
  UNREADABLE_FILE: (d) =>
    `${d?.file ? `${d.file}: ` : ""}파일을 읽을 수 없습니다. 파일이 손상되지 않았는지, 엑셀 또는 CSV 형식이 맞는지 확인해주세요.`,
  MISSING_COLUMNS: (d) =>
    `${d?.file ? `${d.file}: ` : ""}필수 컬럼이 없습니다${Array.isArray(d?.missing) ? ` (${d.missing.join(", ")})` : ""}.`,
  INVALID_NUMBER: (d) =>
    `${d?.file ? `${d.file}: ` : ""}숫자로 읽을 수 없는 값이 있습니다${d?.row ? ` (${d.row}행${d?.column ? ` · ${d.column}` : ""})` : ""}.`,
  UNSUPPORTED_DATASET: (d) =>
    `${d?.file ? `${d.file}: ` : ""}스마트스토어 ${d?.dataset ?? ""} 분석 파일은 아직 지원하지 않습니다. 판매 분석(SALES) 파일을 올려주세요.`,
  INVALID_PERIOD: (d) =>
    d?.needs_input
      ? `${d.file}: 파일에 기간 정보가 없습니다. 파일 목록에서 월을 선택해주세요.`
      : `${d?.file ? `${d.file}: ` : ""}기간(YYYY-MM)을 찾을 수 없습니다. 파일명에 월을 넣어주세요 (예: coupang_2026-09.csv).`,
  UNKNOWN_PLATFORM: (d) => `${d?.file ? `${d.file}: ` : ""}쿠팡·네이버 리포트 형식이 아닙니다.`,
  QUESTION_TOO_LONG: () => `질문은 ${MAX_QUESTION_LENGTH}자 이내로 입력해주세요.`,
  INTERNAL_ERROR: () => "서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
};

export const messageFor = (code: string, fallback: string, details?: Record<string, unknown>) =>
  MESSAGES[code]?.(details) ?? fallback;

async function postForm<T>(path: string, form: FormData): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, { method: "POST", body: form });
  } catch {
    throw new ApiRequestError("NETWORK_ERROR", "서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.");
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const err = (body as ApiError | null)?.error;
    const code = err?.code ?? "INTERNAL_ERROR";
    throw new ApiRequestError(code, messageFor(code, err?.message ?? "알 수 없는 오류가 발생했습니다.", err?.details), err?.details);
  }
  return body as T;
}

function filesForm(files: File[]) {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  return form;
}

export async function previewFiles(files: File[]): Promise<PreviewResponse> {
  if (USE_MOCK) return mockPreview(files);
  return postForm("/api/preview", filesForm(files));
}

/** periods: 파일에 기간 정보가 없어 사용자가 입력한 월 { 파일명: "YYYY-MM" } */
export async function analyzeFiles(
  files: File[],
  question?: string,
  periods?: Record<string, string>,
): Promise<AnalyzeResponse> {
  if (USE_MOCK) return mockAnalyze(files, question);
  const form = filesForm(files);
  if (question) form.append("question", question);
  if (periods && Object.keys(periods).length) form.append("periods", JSON.stringify(periods));
  return postForm("/api/analyze", form);
}

export function validateFiles(files: File[]): string | null {
  if (files.length === 0) return "업로드할 파일을 선택해주세요.";
  if (files.length > MAX_FILES) return `파일은 최대 ${MAX_FILES}개까지 업로드할 수 있습니다.`;
  for (const f of files) {
    const ext = f.name.slice(f.name.lastIndexOf(".")).toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) return `${f.name}: .xlsx 또는 .csv 파일만 업로드할 수 있습니다.`;
    if (f.size > MAX_FILE_SIZE) return `${f.name}: 파일 크기는 5MB 이하여야 합니다.`;
  }
  return null;
}
