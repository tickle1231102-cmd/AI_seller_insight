import type { Platform } from "@/types/api";

export const formatWon = (v: number) => `${Math.round(v).toLocaleString("ko-KR")}원`;

export const formatCount = (v: number, unit: string) => `${Math.round(v).toLocaleString("ko-KR")}${unit}`;

export const formatPercent = (v: number | null) => (v === null ? "-" : `${v.toFixed(1)}%`);

export const formatSignedPercent = (v: number | null, unit = "%") =>
  v === null ? "-" : `${v > 0 ? "+" : ""}${v.toFixed(1)}${unit}`;

export const formatBytes = (b: number) =>
  b < 1024 ? `${b}B` : b < 1024 * 1024 ? `${(b / 1024).toFixed(1)}KB` : `${(b / 1024 / 1024).toFixed(1)}MB`;

export const PLATFORM_LABEL: Record<Platform, string> = {
  coupang: "쿠팡",
  naver: "네이버",
  naver_store: "네이버 스토어",
};

export const platformLabel = (p: string) => PLATFORM_LABEL[p as Platform] ?? p;
