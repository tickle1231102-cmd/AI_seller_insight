"""담당: C — TECH_SPEC 6장 참고.

아래 함수 이름·시그니처는 B 의 routers/analyze.py 가 호출하는 계약이다.
"""

LOW_ROAS_RATIO = 0.8  # 플랫폼 ROAS 가 전체 ROAS 의 이 비율 미만이면 LOW_ROAS_PLATFORM


def detect_signals(kpis: dict, comparison: dict) -> list[dict]:
    """kpis·comparison → TECH_SPEC 6장 신호 목록 (각 항목에 signal, platform 포함). 없으면 []."""
    change = kpis["change"]
    result: list[dict] = []

    ad_spend_change = change["ad_spend_change"]
    roas_change_pp = change["roas_change_pp"]
    if ad_spend_change is not None and roas_change_pp is not None and ad_spend_change > 0 and roas_change_pp < 0:
        result.append(
            {
                "signal": "ROAS_DOWN_WITH_SPEND_GROWTH",
                "platform": "all",
                "ad_spend_change": ad_spend_change,
                "ad_revenue_change": change["ad_revenue_change"],
                "roas_change_pp": roas_change_pp,
            }
        )

    revenue_change = change["revenue_change"]
    if revenue_change is not None and revenue_change < 0:
        result.append({"signal": "REVENUE_DOWN", "platform": "all", "revenue_change": revenue_change})

    overall_roas = kpis["current"]["roas"]
    if overall_roas is not None:
        for item in comparison["by_platform"]:
            roas = item["roas"]
            if roas is not None and roas < overall_roas * LOW_ROAS_RATIO:
                result.append(
                    {"signal": "LOW_ROAS_PLATFORM", "platform": item["platform"], "roas": roas, "overall_roas": overall_roas}
                )
    return result
