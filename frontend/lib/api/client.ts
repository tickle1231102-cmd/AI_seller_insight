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
    throw new ApiRequestError(err?.code ?? "INTERNAL_ERROR", err?.message ?? "알 수 없는 오류가 발생했습니다.", err?.details);
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

export async function analyzeFiles(files: File[], question?: string): Promise<AnalyzeResponse> {
  if (USE_MOCK) return mockAnalyze(files, question);
  const form = filesForm(files);
  if (question) form.append("question", question);
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
