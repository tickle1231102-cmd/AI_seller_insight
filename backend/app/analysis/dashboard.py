"""Display-only dashboard aggregates. No LLM, no changes to existing KPI contracts.

Missing source fields and unobserved cells remain unknown rather than synthetic 0.
Source records are private attrs from the normalizer, consumed before dataframe edits.
"""

from collections import defaultdict

BASE = ("revenue", "orders", "units", "ad_spend", "ad_revenue")
STORE = ("visits", "orders", "units", "gross_revenue", "revenue", "refund_count", "refund_amount", "discount_amount")
RATIOS = {
    "roas": ("ad_revenue", "ad_spend"), "conversion_rate": ("orders", "visits"),
    "net_ratio": ("revenue", "gross_revenue"), "refund_rate": ("refund_count", "orders"),
    "refund_amount_rate": ("refund_amount", "gross_revenue"), "discount_rate": ("discount_amount", "gross_revenue"),
    "aov": ("gross_revenue", "orders"),
}
PRODUCT_LIMIT = 10


def capture_dashboard_source(parsed):
    source = parsed.export.key if parsed.export else "smartstore_sales" if parsed.is_smartstore else "template"
    return [
        {"period": period, "platform": parsed.platform, "source": source,
         "product_id": parsed.product_ids[i], "product_name": parsed.product_names[i],
         "values": {field: int(round(parsed.metrics[column][i])) if parsed.observed[column][i] else None
                    for field, column in parsed.field_map.items()}}
        for i, period in enumerate(parsed.periods)
    ]


def _ratio(values, name):
    numerator, denominator = RATIOS[name]
    n, d = values.get(numerator), values.get(denominator)
    return None if n is None or d is None or d <= 0 else n / d * (1 if name == "aov" else 100)


def _values(rows, fields):
    values = {}
    for field in fields:
        cells = [r["values"][field] for r in rows if field in r["values"]]
        values[field] = sum(cells) if cells and all(v is not None for v in cells) else None
    for name, (num, den) in RATIOS.items():
        if num in fields and den in fields:
            raw = _ratio(values, name)
            values[name] = None if raw is None else round(raw, 0 if name == "aov" else 1)
    return values


def _change(current, previous):
    out = {}
    for field, cur in current.items():
        prev = previous.get(field)
        if field in RATIOS and field != "aov":
            cur, prev = _ratio(current, field), _ratio(previous, field)
            out[field] = None if cur is None or prev is None else round(cur - prev, 1)
        else:
            out[field] = None if cur is None or prev is None or prev == 0 else round((cur - prev) / prev * 100, 1)
    return out


def _month(rows, period):
    selected = [r for r in rows if r["period"] == period]
    return {"period": period, "has_data": bool(selected), "values": _values(selected, BASE),
            "store_values": _values([r for r in selected if r["source"] == "smartstore_sales"], STORE),
            "has_sales": any("revenue" in r["values"] for r in selected),
            "has_ads": any("ad_spend" in r["values"] for r in selected)}


def _products(rows, period, previous_period):
    groups = defaultdict(list)
    for r in rows:
        # Only verified Coupang option IDs bridge sales/ads. Naver sources never join.
        source = "coupang_export" if r["source"] in ("coupang_sales", "coupang_ads") else r["source"]
        if r["source"] == "smartstore_sales" and "전체" in (r["product_id"], r["product_name"]):
            continue
        groups[(source, r["product_id"])].append(r)
    by_source = defaultdict(list)
    for (source, pid), group in sorted(groups.items()):
        cur = [r for r in group if r["period"] == period]
        if not cur:
            continue
        fields = tuple(dict.fromkeys((*BASE, *STORE))) if source == "smartstore_sales" else BASE
        values = _values(cur, fields)
        prev = _values([r for r in group if r["period"] == previous_period], fields)
        by_source[source].append({"product_id": pid, "product_name": sorted(r["product_name"] for r in cur)[0],
                                  "values": values, "change": _change(values, prev)})
    result = []
    for source, products in sorted(by_source.items()):
        sort_key = "gross_revenue" if source == "smartstore_sales" else "ad_spend" if source == "naver_ads" else "revenue"
        products.sort(key=lambda r: (r["values"].get(sort_key) is None, -(r["values"].get(sort_key) or 0), r["product_id"]))
        result.append({"source": source, "sort_key": sort_key, "total": len(products), "items": products[:PRODUCT_LIMIT]})
    return result


def build_dashboard(df, period):
    from app.analysis.kpi import previous_calendar_month

    # Older/mock callers without provenance retain the previous dashboard UI.
    records = df.attrs.get("dashboard_sources")
    if records is None:
        return None
    previous_period = previous_calendar_month(period)
    # Match core_rows exactly, including its existing legacy-template precedence.
    legacy = (df["platform"] == "naver") & (df[list(BASE[:3])].sum(axis=1) > 0)
    overlapping = set(df.loc[legacy, "period"])
    core = [r for r in records if not (r["platform"] == "naver_store" and r["period"] in overlapping)]
    platforms = []
    for platform in ("coupang", "naver"):
        raw = [r for r in records if ("naver" if r["platform"] == "naver_store" else r["platform"]) == platform]
        if not raw:
            continue
        scoped = [r for r in core if ("naver" if r["platform"] == "naver_store" else r["platform"]) == platform]
        current, previous = _month(scoped, period), _month(scoped, previous_period)
        # Store details have their own definition; keep them even when excluded from core KPI.
        for month in (current, previous):
            month["store_values"] = _values([r for r in raw if r["period"] == month["period"] and r["source"] == "smartstore_sales"], STORE)
        periods = sorted({r["period"] for r in raw})
        trend = [_month(scoped, p) for p in periods]
        for month in trend:
            month["store_values"] = _values([r for r in raw if r["period"] == month["period"] and r["source"] == "smartstore_sales"], STORE)
        platforms.append({"platform": platform, "periods": periods, "current": current, "previous": previous,
                          "change": _change(current["values"], previous["values"]),
                          "store_change": _change(current["store_values"], previous["store_values"]),
                          "has_store": any(r["source"] == "smartstore_sales" for r in raw),
                          "overlap_excluded": period in overlapping and any(r["source"] == "smartstore_sales" for r in raw),
                          "trend": trend, "products": _products(raw, period, previous_period)})
    return {"period": period, "previous_period": previous_period, "platforms": platforms}
