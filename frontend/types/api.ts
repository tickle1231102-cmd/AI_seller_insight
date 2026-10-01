export type Platform = "coupang" | "naver" | "naver_store";

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
  // 스마트스토어 판매 분석 파일의 행에만 있다
  gross_revenue?: number;
  visits?: number;
  refund_count?: number;
  refund_amount?: number;
  discount_amount?: number;
}

export interface StoreValues {
  visits: number;
  orders: number;
  units: number;
  gross_revenue: number;
  revenue: number;
  refund_count: number;
  refund_amount: number;
  discount_amount: number;
  conversion_rate: number | null;
  net_ratio: number | null;
  refund_rate: number | null;
  refund_amount_rate: number | null;
  discount_rate: number | null;
  aov: number | null;
}

export interface StoreChange {
  visits_change: number | null;
  orders_change: number | null;
  gross_revenue_change: number | null;
  revenue_change: number | null;
  aov_change: number | null;
  conversion_rate_change_pp: number | null;
  net_ratio_change_pp: number | null;
  refund_rate_change_pp: number | null;
  refund_amount_rate_change_pp: number | null;
  discount_rate_change_pp: number | null;
}

export interface StoreProduct {
  product_id: string;
  product_name: string;
  visits: number;
  orders: number;
  gross_revenue: number;
  revenue: number;
  conversion_rate: number | null;
  refund_rate: number | null;
  discount_rate: number | null;
  aov: number | null;
  refund_rate_change_pp: number | null;
  conversion_rate_change_pp: number | null;
}

export interface StoreTrendPoint {
  period: string;
  visits: number;
  orders: number;
  revenue: number;
  conversion_rate: number | null;
}

export interface StoreKpis {
  period: string;
  previous_period: string | null;
  current: StoreValues;
  previous: StoreValues | null;
  change: StoreChange;
  products: StoreProduct[];
  trend: StoreTrendPoint[];
}

// 쿠팡 판매 분석 (옵션별 지표: 퍼널·취소)
export interface CoupangValues {
  visits: number;
  views: number;
  cart_adds: number;
  orders: number;
  units: number;
  gross_revenue: number; // 총 매출(원)
  revenue: number; // 매출(원), 취소 반영
  gross_units: number;
  cancel_units: number;
  cancel_amount: number;
  conversion_rate: number | null; // 주문/방문자 (%)
  cart_rate: number | null; // 장바구니/방문자 (%)
  cancel_rate: number | null; // 취소 상품수/총 판매수 (%)
  cancel_amount_rate: number | null; // 취소 금액/총 매출 (%)
  aov: number | null; // 매출/주문
}

export interface CoupangChange {
  visits_change: number | null;
  orders_change: number | null;
  revenue_change: number | null;
  aov_change: number | null;
  conversion_rate_change_pp: number | null;
  cart_rate_change_pp: number | null;
  cancel_rate_change_pp: number | null;
  cancel_amount_rate_change_pp: number | null;
}

export interface CoupangProduct {
  product_id: string; // 옵션 ID
  product_name: string; // 옵션명
  visits: number;
  cart_adds: number;
  orders: number;
  revenue: number;
  conversion_rate: number | null;
  cart_rate: number | null;
  cancel_rate: number | null;
  aov: number | null;
  conversion_rate_change_pp: number | null;
  cancel_rate_change_pp: number | null;
}

export interface CoupangKpis {
  period: string;
  previous_period: string | null;
  current: CoupangValues;
  previous: CoupangValues | null;
  change: CoupangChange;
  products: CoupangProduct[];
  trend: StoreTrendPoint[];
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
  store?: StoreKpis | null; // 스마트스토어 판매 분석 파일이 없으면 null
  coupang?: CoupangKpis | null; // 쿠팡 판매 분석(옵션별 지표) 파일이 없으면 null
  dashboard?: Dashboard | null;
}

export type DashboardValues = Record<string, number | null>;
export interface DashboardMonth {
  period: string;
  has_data: boolean;
  has_sales: boolean;
  has_ads: boolean;
  values: DashboardValues;
  store_values: DashboardValues;
}
export interface DashboardProducts {
  source: string;
  sort_key: string;
  total: number;
  items: { product_id: string; product_name: string; values: DashboardValues; change: DashboardValues }[];
}
export interface DashboardPlatform {
  platform: "coupang" | "naver";
  periods: string[];
  current: DashboardMonth;
  previous: DashboardMonth;
  change: DashboardValues;
  store_change: DashboardValues;
  has_store: boolean;
  overlap_excluded: boolean;
  trend: DashboardMonth[];
  products: DashboardProducts[];
}
export interface Dashboard {
  period: string;
  previous_period: string;
  platforms: DashboardPlatform[];
}
