"""D-owned evidence catalogue. Values are copied from C, never recalculated.

The model selects references; only this module renders factual sentences.
Source paths retain the metric, entity, unit and period of every value.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
import json
import re
from typing import Any

from .models import AnalysisPlan


METRICS = {
    "revenue": ("매출", "원"), "orders": ("주문 수", "건"),
    "units": ("판매 수량", "개"), "ad_spend": ("광고비", "원"),
    "ad_revenue": ("광고 전환매출", "원"), "roas": ("ROAS", "%"),
}
PERIOD = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def number(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def period_label(value: Any) -> str:
    return value if isinstance(value, str) and PERIOD.fullmatch(value) else "기간 미지정"


def entity(row: Mapping[str, Any]) -> str:
    parts = []
    if row.get("platform"):
        parts.append({"coupang": "쿠팡", "naver": "네이버", "all": "전체"}.get(
            str(row["platform"]), json.dumps(str(row["platform"]), ensure_ascii=False)))
    if row.get("product_id") is not None:
        parts.append("상품 ID " + json.dumps(str(row["product_id"]), ensure_ascii=False))
    if row.get("product_name") is not None:
        # Quoted source labels are data, never interpreted as model instructions.
        parts.append("상품명 " + json.dumps(str(row["product_name"]), ensure_ascii=False))
    return " / ".join(parts) or "전체"


@dataclass(frozen=True)
class Fact:
    id: str
    period: str
    entity: str
    metric: str
    value: str
    unit: str
    text: str

    def payload(self) -> dict[str, str]:
        return dict(vars(self))


@dataclass
class EvidenceCatalogue:
    facts: dict[str, Fact] = field(default_factory=dict)
    checks: dict[str, str] = field(default_factory=lambda: {
        "check_source": "업로드한 파일의 대상 기간과 누락 여부를 확인하세요.",
    })
    actions: dict[str, str] = field(default_factory=lambda: {
        "verify_before_change": "예산이나 운영 방식을 변경하기 전에 해당 기간의 원자료를 확인하세요.",
    })
    limitations: list[str] = field(default_factory=lambda: [
        "분석 범위는 업로드된 자료에 한정됩니다. 전체 시장의 상황을 의미하지 않습니다.",
        "현재 자료만으로 광고 소재·CTR·CPC·CVR·경쟁사 가격이 성과에 미친 원인을 확정할 수 없습니다. "
        "원인 확인에는 소재별 노출·클릭·전환 자료와 가격 이력 등이 필요합니다.",
    ])
    answer_ids: list[str] = field(default_factory=list)
    default_ids: list[str] = field(default_factory=list)
    conflicts: list[tuple[str, str]] = field(default_factory=list)

    def add(self, path: str, row: Mapping[str, Any], period: Any, scope: str,
            *, metrics: Sequence[str] = tuple(METRICS), change_from: Any = None) -> None:
        for metric in metrics:
            value = number(row.get(metric))
            if value is None:
                continue
            base = metric.removesuffix("_change_pp").removesuffix("_change")
            if base not in METRICS:
                continue
            label, unit = METRICS[base]
            value_text = format(value, ",f")
            if "." in value_text:
                value_text = value_text.rstrip("0").rstrip(".")
            when = period_label(period)
            if metric.endswith(("_change", "_change_pp")):
                unit = "%p" if metric.endswith("_change_pp") else "%"
                label += " 증감" if unit == "%p" else " 증감률"
                if value > 0:
                    value_text = "+" + value_text
                when = f"{period_label(change_from)} → {when}"
            fid = f"{path}.{metric}"
            self.facts[fid] = Fact(fid, when, scope, metric, str(value), unit,
                                  f"{when} / {scope} / {label}: {value_text}{unit}.")

    @classmethod
    def build(cls, kpis: Mapping[str, Any], comparison: Mapping[str, Any],
              signals: Sequence[Mapping[str, Any]], plan: AnalysisPlan | None,
              answer: Sequence[Mapping[str, Any]] | None) -> EvidenceCatalogue:
        c = cls()
        current = kpis.get("current", kpis)
        period, previous = kpis.get("period"), kpis.get("previous_period")
        if isinstance(current, Mapping):
            c.add("kpis.current", current, period, "전체")
            if current.get("roas") is None:
                c.limitations.append("현재 ROAS는 계산 가능한 값이 없어 효율의 높고 낮음을 판단할 수 없습니다.")
        if isinstance(kpis.get("previous"), Mapping):
            c.add("kpis.previous", kpis["previous"], previous, "전체")
        change = kpis.get("change")
        if isinstance(change, Mapping) and previous:
            c.add("kpis.change", change, period, "전체", metrics=tuple(change), change_from=previous)
            unavailable = [METRICS[m.removesuffix("_change_pp").removesuffix("_change")][0]
                           for m, v in change.items() if v is None
                           and m.removesuffix("_change_pp").removesuffix("_change") in METRICS]
            if unavailable:
                c.limitations.append("비교 불가 지표: " + ", ".join(unavailable) + ". 누락된 비교값 또는 분모를 확인하세요.")
        else:
            c.limitations.append("비교할 이전 기간 자료가 없어 전월 대비 증가·감소를 판단할 수 없습니다.")
        if PERIOD.fullmatch(str(period)) and PERIOD.fullmatch(str(previous)):
            y, m = map(int, str(period).split("-"))
            py, pm = map(int, str(previous).split("-"))
            if y * 12 + m - (py * 12 + pm) != 1:
                c.limitations.append("비교 기간은 연속된 달이 아닙니다. 표시된 두 기간의 차이로 해석하세요.")
        for i, row in enumerate(comparison.get("by_platform", [])):
            c.add(f"comparison.by_platform.{i}", row, period, entity(row))
        for i, row in enumerate(comparison.get("trend", [])):
            c.add(f"comparison.trend.{i}", row, row.get("period"), "전체")
        for i, row in enumerate(answer or []):
            row_period = row.get("period") or (plan.period if plan else None) or period
            start = set(c.facts)
            c.add(f"answer.{i}", row, row_period, entity(row),
                  metrics=[plan.metric] if plan else tuple(METRICS))
            c.answer_ids.extend(fid for fid in c.facts if fid not in start)
            if plan and number(row.get(plan.metric)) is None:
                c.limitations.append(f"질문 결과의 {entity(row)} / {METRICS[plan.metric][0]}는 계산 불가로 순위 판단에서 제외합니다.")
        if plan:
            scope = ("업로드된 여러 기간" if plan.group_by == "period" and plan.period is None
                     else period_label(plan.period or period))
            c.limitations.append(f"질문 결과 범위: {scope}. 반환된 결과에 한해 설명합니다.")
        if not signals:
            c.limitations.append("등록된 이상 신호가 없다는 사실만으로 문제가 없다고 단정할 수 없습니다.")
        for signal in signals:
            name = signal.get("signal")
            if name == "ROAS_DOWN_WITH_SPEND_GROWTH" and isinstance(change, Mapping):
                spend, roas = number(change.get("ad_spend_change")), number(change.get("roas_change_pp"))
                if spend is not None and roas is not None and spend > 0 and roas < 0:
                    c.checks["check_spend_roas"] = "광고비 증가와 ROAS 하락이 함께 나타난 기간의 집행 내역을 확인하세요."
                    c.actions["review_ad_spend"] = "광고비 조정에 앞서 캠페인별 비용과 전환매출 자료를 대조하세요."
            elif name == "REVENUE_DOWN" and isinstance(change, Mapping):
                value = number(change.get("revenue_change"))
                if value is not None and value < 0:
                    c.checks["check_revenue"] = "매출 감소가 발생한 기간의 상품별 매출과 주문 자료를 확인하세요."
                    c.actions["review_revenue"] = "원인을 확정하기 전에 가격·수량·반품 등 필요한 추가 자료를 수집하세요."
            elif name == "LOW_ROAS_PLATFORM":
                for i, row in enumerate(comparison.get("by_platform", [])):
                    fid = f"comparison.by_platform.{i}.roas"
                    if row.get("platform") == signal.get("platform") and fid in c.facts:
                        c.checks[f"check_platform_{i}"] = f"{entity(row)}의 광고 집행 내역과 전환매출을 확인하세요."
                        c.actions[f"review_platform_{i}"] = f"{entity(row)}의 예산 변경 전에 캠페인별 성과 자료를 추가 확인하세요."
        c.default_ids = c.answer_ids[:3] or [fid for fid in (
            "kpis.current.revenue", "kpis.current.roas", "kpis.change.revenue_change",
            "kpis.change.roas_change_pp") if fid in c.facts][:3] or list(c.facts)[:3]
        c.limitations = list(dict.fromkeys(c.limitations))
        # Sources with the same scope must agree. Never let AI reconcile them.
        seen: dict[tuple[str, str, str, str], Fact] = {}
        for fact in c.facts.values():
            key = (fact.period, fact.entity, fact.metric, fact.unit)
            if key in seen and number(seen[key].value) != number(fact.value):
                c.conflicts.append((seen[key].id, fact.id))
            seen[key] = fact
        return c

    def payload(self) -> dict[str, Any]:
        return {"facts": [f.payload() for f in self.facts.values()],
                "required_answer_fact_ids": self.answer_ids[:3],
                "checks": self.checks, "actions": self.actions,
                "limitations": self.limitations}
