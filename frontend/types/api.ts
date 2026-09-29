export type Platform = "coupang" | "naver";

export interface ApiError {
  error: { code: string; message: string; details?: Record<string, unknown> };
}

export interface PreviewFile {
  filename: string;
  platform: Platform;
  periods: string[];
  row_count: number;
  columns: string[];
  preview: Record<string, string | number | null>[];
}

export interface PreviewResponse {
  files: PreviewFile[];
}

export interface KpiValues {
  revenue: number;
  orders: number;
  units: number;
  ad_spend: number;
  ad_revenue: number;
  roas: number | null;
}

export interface KpiChange {
  revenue_change: number | null;
  orders_change: number | null;
  units_change: number | null;
  ad_spend_change: number | null;
  ad_revenue_change: number | null;
  roas_change_pp: number | null;
}

export interface Kpis {
  period: string;
  previous_period: string | null;
  current: KpiValues;
  previous: KpiValues | null;
  change: KpiChange;
}

export interface PlatformComparison {
  platform: Platform;
  revenue: number;
  orders: number;
  ad_spend: number;
  ad_revenue: number;
  roas: number | null;
}

export interface TrendPoint {
  period: string;
  revenue: number;
  roas: number | null;
}

export interface Comparison {
  by_platform: PlatformComparison[];
  trend: TrendPoint[];
}

export interface NormalizedRow {
  period: string;
  platform: Platform;
  product_id: string;
  product_name: string;
  revenue: number;
  orders: number;
  units: number;
  ad_spend: number;
  ad_revenue: number;
}

export type SignalCode =
  | "ROAS_DOWN_WITH_SPEND_GROWTH"
  | "REVENUE_DOWN"
  | "LOW_ROAS_PLATFORM";

export interface Signal {
  signal: SignalCode;
  platform: string;
  [key: string]: string | number | null;
}

export type InsightStatus = "ok" | "unsupported_question" | "llm_error" | "skipped";

export interface Insight {
  status: InsightStatus;
  plan?: Record<string, unknown> | null;
  answer?: Record<string, unknown>[] | null;
  summary?: string;
  evidence?: string[];
  checks?: string[];
  actions?: string[];
  limitations?: string[];
}

export interface AnalyzeResponse {
  kpis: Kpis;
  comparison: Comparison;
  rows: NormalizedRow[];
  signals: Signal[];
  insight: Insight;
}
