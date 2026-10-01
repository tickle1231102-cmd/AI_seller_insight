"""C: reproducible monthly product screening, with no model-generated scores."""
from __future__ import annotations

from collections import defaultdict
import math
from statistics import median

from app.analysis.diagnosis_sources import BASE_FIELDS, STORE_FIELDS, source_rows
from app.analysis.kpi import previous_calendar_month
from app.core.errors import AppError

INTENTS = {"opportunity", "attention"}
CONDITION_METRICS = {"revenue_up": "revenue_change", "ad_spend_down": "ad_spend_change",
                     "ad_spend_up": "ad_spend_change", "ad_revenue_down": "ad_revenue_change",
                     "ad_revenue_not_up": "ad_revenue_change", "roas_down": "roas_change_pp"}
CONDITIONS = set(CONDITION_METRICS)
OPPORTUNITY_REASONS = ("REVENUE_GROWTH", "SALES_VOLUME_GROWTH", "GOOD_ROAS", "REVENUE_GROWTH_GT_AD_SPEND")
ATTENTION_REASONS = ("REVENUE_DECLINE", "SALES_VOLUME_DECLINE", "ROAS_DECLINE", "AD_SPEND_UP_WITH_WEAK_RETURN", "STORE_QUALITY_DECLINE")
SCOPE_LABELS = {"template": "통합 템플릿", "coupang_export": "쿠팡 옵션 ID", "naver_ads": "네이버 광고 소재 ID", "smartstore_sales": "스마트스토어 상품 ID"}
RATES = {"roas": ("ad_revenue", "ad_spend"), "conversion_rate": ("orders", "visits"),
         "refund_rate": ("refund_count", "orders"), "discount_rate": ("discount_amount", "gross_revenue")}


def _number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def _ratio(numerator, denominator, scale=100):
    if numerator is None or denominator is None or denominator <= 0 or numerator < 0:
        return None
    return numerator / denominator * scale


def _change(current, previous):
    if current is None or previous is None or previous <= 0:
        return None
    return round((current - previous) / previous * 100, 1)


def _up(value):
    return value is not None and value > 0


def _down(value):
    return value is not None and value < 0


def rule_results(row: dict, intent: str) -> dict[str, bool | None]:
    """None = insufficient evidence, not a false/zero observation."""
    def sign(value, positive):
        return None if value is None else value > 0 if positive else value < 0
    def either(a, b):
        if a is True or b is True:
            return True
        return False if a is False and b is False else None
    if intent == "opportunity":
        r, spend, roas, benchmark = (row[k] for k in ("revenue_change", "ad_spend_change", "roas", "benchmark_roas"))
        return dict(zip(OPPORTUNITY_REASONS, (
            sign(r, True), either(sign(row["orders_change"], True), sign(row["units_change"], True)),
            None if roas is None or benchmark is None else roas >= benchmark,
            None if r is None or spend is None else r > spend,
        )))
    spend, ad = row["ad_spend_change"], row["ad_revenue_change"]
    return dict(zip(ATTENTION_REASONS, (
        sign(row["revenue_change"], False),
        either(sign(row["orders_change"], False), sign(row["units_change"], False)),
        sign(row["roas_change_pp"], False),
        None if spend is None or ad is None else spend > 0 and ad <= 0,
        either(sign(row["refund_rate_change_pp"], True), sign(row["conversion_rate_change_pp"], False)),
    )))


def condition_matches(row: dict, condition: str) -> bool:
    return {
        "revenue_up": lambda: _up(row["revenue_change"]),
        "ad_spend_down": lambda: _down(row["ad_spend_change"]),
        "ad_spend_up": lambda: _up(row["ad_spend_change"]),
        "ad_revenue_down": lambda: _down(row["ad_revenue_change"]),
        "ad_revenue_not_up": lambda: row["ad_revenue_change"] is not None and row["ad_revenue_change"] <= 0,
        "roas_down": lambda: _down(row["roas_change_pp"]),
    }[condition]()


def _monthly_products(df) -> dict:
    groups = defaultdict(list)
    for row in source_rows(df):
        if not row["product_id"] or "전체" in (row["product_id"], row["product_name"]):
            continue  # total rows are never products
        source = row["source"]
        scope = "coupang_export" if source in {"coupang_sales", "coupang_ads"} else source
        # Only Coupang's identical option IDs may join sales and ads. Naver
        # creative IDs and SmartStore product IDs remain different namespaces.
        groups[(row["period"], row["platform"], scope, row["product_id"])].append(row)
    result = {}
    for key, rows in groups.items():
        metrics = {}
        for field in (*BASE_FIELDS, *STORE_FIELDS):
            values = [_number(r["metrics"][field]) for r in rows if field in r["metrics"]]
            metrics[field] = sum(values) if values and all(v is not None for v in values) else None
        for metric, (num, den) in RATES.items():
            metrics[metric] = _ratio(metrics[num], metrics[den])
        metrics["aov"] = _ratio(metrics["gross_revenue"], metrics["orders"], 1)
        result[key] = {"product_name": min(r["product_name"] for r in rows), **metrics}
    return result


def run_product_diagnosis(df, intent: str, limit: int = 5, *, period: str | None = None,
                          required_conditions: list[str] | None = None) -> list[dict]:
    """Latest (or requested) month vs calendar previous month, per platform/ID.

    Opportunities require revenue AND order/unit growth. Attention needs at
    least one adverse rule. Scores count only observed, satisfied rules.
    Missing/new/disappeared products are excluded rather than zero-filled.
    """
    required = required_conditions or []
    if intent not in INTENTS or type(limit) is not int or not 1 <= limit <= 50 or any(c not in CONDITIONS for c in required):
        raise AppError("UNSUPPORTED_PLAN", "상품 진단의 종류·개수·조건을 확인해주세요.", 422)
    available = sorted(df["period"].unique())
    if not available:
        raise AppError("DIAGNOSIS_INSUFFICIENT_PERIODS", "추세를 판단하려면 같은 상품의 최소 2개월 자료가 필요해요.", 422)
    period = period or available[-1]
    if period not in available:
        raise AppError("PERIOD_NOT_FOUND", f"{period} 자료가 없어요. 업로드된 기간: {', '.join(available)}.", 422)
    previous = previous_calendar_month(period)
    if previous not in available:
        raise AppError("DIAGNOSIS_INSUFFICIENT_PERIODS", f"추세 판단에 기간이 부족해요. {period}와 달력상 전월({previous})의 동일 상품 자료를 함께 올려주세요. 최소 2개월이 필요합니다.", 422)
    products = _monthly_products(df)
    pairs = [(key, cur, products[(previous, *key[1:])]) for key, cur in products.items()
             if key[0] == period and (previous, *key[1:]) in products]
    if not pairs:
        raise AppError("DIAGNOSIS_NO_COMPARABLE_PRODUCTS", "최신월과 전월에 공통으로 있는 상품 ID를 찾지 못했어요. 같은 플랫폼·자료 종류의 동일 상품 자료가 필요합니다.", 422)
    benchmarks = defaultdict(list)
    for (_, platform, scope, _), cur, _ in pairs:
        if cur["roas"] is not None:
            benchmarks[(platform, scope)].append(round(cur["roas"], 1))
    result, evaluated_any = [], False
    for (_, platform, scope, pid), cur, prev in pairs:
        reference = benchmarks[(platform, scope)]
        row = {"rank": 0, "platform": platform, "product_id": pid, "product_name": cur["product_name"],
               "period": period, "previous_period": previous, "diagnosis": intent, "score": 0,
               "score_max": 4 if intent == "opportunity" else 5, "evaluated_rules": 0,
               "data_scope": SCOPE_LABELS[scope],
               "benchmark_roas": round(median(reference), 1) if reference else None,
               "benchmark_count": len(reference)}
        for metric in (*BASE_FIELDS, "visits", "gross_revenue", "aov"):
            value = cur[metric]
            row[metric] = None if value is None else round(value) if metric == "aov" else value
            row[f"{metric}_change"] = _change(cur[metric], prev[metric])
        for metric in RATES:
            current_rate, previous_rate = cur[metric], prev[metric]
            row[metric] = None if current_rate is None else round(current_rate, 1)
            row[f"{metric}_change_pp"] = (None if current_rate is None or previous_rate is None
                                         else round(current_rate - previous_rate, 1))
        rules = rule_results(row, intent)
        row["reason_codes"] = [code for code, satisfied in rules.items() if satisfied is True]
        row["score"] = len(row["reason_codes"])
        row["evaluated_rules"] = sum(value is not None for value in rules.values())
        evaluable = bool(row["evaluated_rules"]) and all(row[CONDITION_METRICS[c]] is not None for c in required)
        if intent == "opportunity":
            evaluable &= rules["REVENUE_GROWTH"] is not None and rules["SALES_VOLUME_GROWTH"] is not None
        evaluated_any |= evaluable
        if intent == "opportunity" and not (rules["REVENUE_GROWTH"] and rules["SALES_VOLUME_GROWTH"]):
            continue
        if row["score"] and all(condition_matches(row, condition) for condition in required):
            result.append(row)
    if not evaluated_any:
        raise AppError("DIAGNOSIS_INSUFFICIENT_METRICS", "상품 진단에 필요한 전월 비교 지표를 계산할 수 없어요. 누락된 판매·광고 지표와 0인 전월 기준값을 확인해주세요.", 422)
    def descending(value):
        return (value is None, -value if value is not None else 0)
    if intent == "opportunity":
        result.sort(key=lambda r: (-r["score"], *descending(r["revenue_change"]), *descending(r["roas"]),
                                   *descending(r["revenue"]), r["platform"], r["data_scope"], r["product_id"]))
    else:
        result.sort(key=lambda r: (-r["score"], r["revenue_change"] is None, r["revenue_change"] or 0,
                                   r["roas_change_pp"] is None, r["roas_change_pp"] or 0,
                                   *descending(r["revenue"]), r["platform"], r["data_scope"], r["product_id"]))
    for rank, row in enumerate(result[:limit], 1):
        row["rank"] = rank
    return result[:limit]
