import type { DashboardPlatform, DashboardValues } from "@/types/api";
import { formatCount, formatPercent, formatSignedPercent, formatWon } from "@/lib/format";

export const METRICS: Record<string, { label: string; unit: "won" | "count" | "rate" }> = {
  revenue: { label: "매출액", unit: "won" }, orders: { label: "주문", unit: "count" },
  units: { label: "판매량", unit: "count" }, ad_spend: { label: "광고비", unit: "won" },
  ad_revenue: { label: "광고매출", unit: "won" }, roas: { label: "ROAS", unit: "rate" },
  visits: { label: "방문수", unit: "count" }, gross_revenue: { label: "총매출", unit: "won" },
  refund_count: { label: "환불 건수", unit: "count" }, refund_amount: { label: "환불금액", unit: "won" },
  discount_amount: { label: "할인액", unit: "won" }, conversion_rate: { label: "구매전환율", unit: "rate" },
  net_ratio: { label: "순매출 비율", unit: "rate" }, refund_rate: { label: "환불률(건수)", unit: "rate" },
  refund_amount_rate: { label: "환불금액 비율", unit: "rate" }, discount_rate: { label: "할인율", unit: "rate" },
  aov: { label: "결제단가", unit: "won" },
};
export const SALES = ["revenue", "orders", "units"];
export const ADS = ["ad_spend", "ad_revenue", "roas"];
export const STORE = ["visits", "orders", "units", "gross_revenue", "revenue", "refund_count", "refund_amount", "discount_amount", "conversion_rate", "net_ratio", "refund_rate", "refund_amount_rate", "discount_rate", "aov"];
export const SOURCE_LABEL: Record<string, string> = {
  coupang_export: "쿠팡 옵션별 판매·광고", template: "통합 템플릿", smartstore_sales: "스마트스토어 판매 상품", naver_ads: "네이버 광고 소재",
};
export const label = (p: DashboardPlatform) => p.platform === "coupang" ? "쿠팡" : p.has_store ? "네이버 스마트스토어" : p.current.has_sales ? "네이버" : "네이버 광고";
export function metricValue(field: string, value: number | null | undefined) {
  if (value == null || !Number.isFinite(value)) return "—";
  return METRICS[field]?.unit === "won" ? formatWon(value) : METRICS[field]?.unit === "rate" ? formatPercent(value) : formatCount(value, field === "units" ? "개" : field === "visits" ? "회" : "건");
}
export const deltaValue = (field: string, value: number | null | undefined) => value == null ? "비교 불가" : formatSignedPercent(value, METRICS[field]?.unit === "rate" ? "%p" : "%");
export function unavailable(p: DashboardPlatform, field: string) {
  if (!p.current.has_data) return "기준 월 자료 없음";
  if (SALES.includes(field) && !p.current.has_sales) return "판매 자료 없음";
  if (ADS.includes(field) && !p.current.has_ads) return "광고 자료 없음";
  return field === "roas" ? "광고 지표 누락 또는 광고비 0 이하" : "원자료에 빈 값이 있어 합계 확인 필요";
}
export function totalValue(platforms: DashboardPlatform[], field: string): number | null {
  const values = platforms.map((p) => p.current.values[field]);
  return values.length && values.every((v) => v != null) ? values.reduce<number>((sum, v) => sum + v!, 0) : null;
}
export const availableFields = (rows: DashboardValues[], fields: string[]) => fields.filter((field) => rows.some((v) => v[field] != null));
