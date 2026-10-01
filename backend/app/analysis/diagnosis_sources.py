"""Private provenance for product diagnosis; never adds public row columns."""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json

import pandas as pd

from app.core.errors import AppError

SOURCE_ATTR = "product_diagnosis_sources_v1"
BASE_FIELDS = ("revenue", "orders", "units", "ad_spend", "ad_revenue")
STORE_FIELDS = ("gross_revenue", "visits", "refund_count", "refund_amount", "discount_amount")


def fingerprint(df: pd.DataFrame) -> str:
    """Order-independent signature so a filtered/edited frame cannot reuse stale provenance."""
    records = df.astype(object).where(pd.notna(df), None).to_dict("records")
    rows = sorted(json.dumps(r, sort_keys=True, ensure_ascii=False, allow_nan=False) for r in records)
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


def capture_source(parsed) -> list[dict]:
    source = parsed.export.key if parsed.export else "smartstore_sales" if parsed.is_smartstore else "template"
    groups = defaultdict(list)
    for i, (period, pid) in enumerate(zip(parsed.periods, parsed.product_ids)):
        groups[(period, pid)].append(i)
    rows = []
    for (period, pid), indices in sorted(groups.items()):
        metrics = {}
        for metric, column in parsed.field_map.items():
            # An absent/blank cell is unknown for diagnosis, even though the
            # established KPI contract fills it with zero.
            metrics[metric] = (sum(int(round(parsed.metrics[column][i])) for i in indices)
                               if all(parsed.observed[column][i] for i in indices) else None)
        rows.append({"period": period, "platform": parsed.platform, "product_id": pid,
                     "product_name": min(parsed.product_names[i] for i in indices),
                     "source": source, "metrics": metrics})
    return rows


def attach_sources(df: pd.DataFrame, rows: list[dict]) -> pd.DataFrame:
    df.attrs[SOURCE_ATTR] = {"fingerprint": fingerprint(df), "rows": rows}
    return df


def source_rows(df: pd.DataFrame) -> list[dict]:
    meta = df.attrs.get(SOURCE_ATTR)
    if meta is not None:
        if meta.get("fingerprint") != fingerprint(df):
            raise AppError("DIAGNOSIS_SOURCE_MISMATCH", "자료가 변경되어 상품 진단의 원본 지표를 확인할 수 없어요. 파일을 다시 분석해주세요.", 422)
        return meta["rows"]
    # Trusted direct callers may provide canonical, fully observed rows.
    # The HTTP path always uses normalize_files and its source metadata.
    rows = []
    for row in df.to_dict("records"):
        store = row["platform"] == "naver_store"
        fields = ("revenue", "orders", "units", *STORE_FIELDS) if store else BASE_FIELDS
        rows.append({**{k: row[k] for k in ("period", "platform", "product_id", "product_name")},
                     "source": "smartstore_sales" if store else "template",
                     "metrics": {k: (None if pd.isna(row.get(k)) else row[k]) for k in fields if k in row}})
    return rows
