import type { AnalyzeResponse, Insight, PreviewResponse, Platform } from "@/types/api";

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

function guessPlatform(name: string): Platform {
  return /naver|네이버/i.test(name) ? "naver" : "coupang";
}

function guessPeriod(name: string): string {
  return name.match(/\d{4}-\d{2}/)?.[0] ?? "2026-09";
}

export async function mockPreview(files: File[]): Promise<PreviewResponse> {
  await delay(400);
  return {
    files: files.map((f) => {
      const platform = guessPlatform(f.name);
      const columns =
        platform === "coupang"
          ? ["product_name", "총매출", "주문", "판매량", "광고비", "광고매출"]
          : ["product_name", "판매금액(순)", "상품결제건수", "결제상품수량", "광고비용", "전환매출"];
      return {
        filename: f.name,
        platform,
        periods: [guessPeriod(f.name)],
        row_count: 42,
        columns,
        preview: [
          Object.fromEntries(columns.map((c, i) => [c, i === 0 ? "무선 이어폰" : 120000 * i])),
          Object.fromEntries(columns.map((c, i) => [c, i === 0 ? "보조배터리" : 80000 * i])),
        ],
      };
    }),
  };
}

function mockInsight(question?: string): Insight {
  if (!question) {
    return {
      status: "ok",
      summary: "매출은 증가했지만 광고비 증가율이 광고매출 증가율보다 높아 ROAS가 하락했습니다.",
      evidence: ["광고비 +28.0%", "광고매출 +22.4%", "ROAS -14.2%p"],
      checks: ["어느 플랫폼에서 ROAS가 가장 크게 하락했는지 확인", "광고비 증가 대비 주문 증가폭 확인"],
      actions: ["저효율 플랫폼의 광고비를 우선 점검", "예산 조정 전 최근 추이를 추가 확인"],
      limitations: ["현재 데이터만으로 광고 소재·CTR·CPC·CVR 영향은 확인할 수 없습니다."],
    };
  }
  return {
    status: "ok",
    plan: { metric: "roas", group_by: "platform", sort: "asc" },
    answer: [{ platform: "coupang", roas: 291.7 }],
    summary: "쿠팡의 ROAS가 291.7%로 네이버(347.2%)보다 낮아 광고 효율이 가장 낮은 플랫폼입니다.",
    evidence: ["쿠팡 ROAS 291.7%", "네이버 ROAS 347.2%"],
    checks: ["쿠팡 광고비 증가 대비 주문 증가폭 확인"],
    actions: ["쿠팡 광고비 집행 내역을 우선 점검"],
    limitations: ["현재 데이터만으로 광고 소재·CTR·CPC 영향은 확인할 수 없습니다."],
  };
}

export async function mockAnalyze(_files: File[], question?: string): Promise<AnalyzeResponse> {
  await delay(900);
  return {
    kpis: {
      period: "2026-09",
      previous_period: "2026-08",
      current: { revenue: 12600000, orders: 830, units: 1020, ad_spend: 1920000, ad_revenue: 6000000, roas: 312.5 },
      previous: { revenue: 10400000, orders: 700, units: 860, ad_spend: 1500000, ad_revenue: 4900000, roas: 326.7 },
      change: {
        revenue_change: 21.2,
        orders_change: 18.6,
        units_change: 18.6,
        ad_spend_change: 28.0,
        ad_revenue_change: 22.4,
        roas_change_pp: -14.2,
      },
    },
    comparison: {
      by_platform: [
        { platform: "coupang", revenue: 8000000, orders: 520, ad_spend: 1200000, ad_revenue: 3500000, roas: 291.7 },
        { platform: "naver", revenue: 4600000, orders: 310, ad_spend: 720000, ad_revenue: 2500000, roas: 347.2 },
      ],
      trend: [
        { period: "2026-07", revenue: 9800000, roas: 331.0 },
        { period: "2026-08", revenue: 10400000, roas: 326.7 },
        { period: "2026-09", revenue: 12600000, roas: 312.5 },
      ],
    },
    rows: [],
    signals: [
      { signal: "ROAS_DOWN_WITH_SPEND_GROWTH", platform: "all", ad_spend_change: 28.0, ad_revenue_change: 22.4, roas_change_pp: -14.2 },
      { signal: "LOW_ROAS_PLATFORM", platform: "coupang", roas: 291.7, overall_roas: 312.5 },
    ],
    insight: mockInsight(question),
  };
}
