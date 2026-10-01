"""D: render C's rankings/reason codes as grounded, fixed Korean sentences."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import math

from app.analysis.kpi import previous_calendar_month
from app.analysis.product_diagnosis import condition_matches, rule_results

from .facts import METRICS, entity
from .models import Insight, ProductDiagnosisPlan

REASON_METRICS = {
    "REVENUE_GROWTH": ("매출 증가", ("revenue_change",)),
    "SALES_VOLUME_GROWTH": ("주문 또는 판매량 증가", ("orders_change", "units_change")),
    "GOOD_ROAS": ("같은 플랫폼·자료 종류의 비교 상품 중앙값 이상 ROAS", ("roas", "benchmark_roas")),
    "REVENUE_GROWTH_GT_AD_SPEND": ("매출 증가율이 광고비 증가율보다 높음", ("revenue_change", "ad_spend_change")),
    "REVENUE_DECLINE": ("매출 감소", ("revenue_change",)),
    "SALES_VOLUME_DECLINE": ("주문 또는 판매량 감소", ("orders_change", "units_change")),
    "ROAS_DECLINE": ("ROAS 하락", ("roas_change_pp",)),
    "AD_SPEND_UP_WITH_WEAK_RETURN": ("광고비 증가 대비 광고매출 부진", ("ad_spend_change", "ad_revenue_change")),
    "STORE_QUALITY_DECLINE": ("전환율 하락 또는 환불률 상승", ("conversion_rate_change_pp", "refund_rate_change_pp")),
}
LIMITATIONS = [
    "업로드한 동일 플랫폼·자료 종류·상품 ID의 기준 월과 달력상 전월만 비교합니다. 세 달 이상 있어도 이번 진단은 두 달 비교입니다.",
    "점수는 확인된 조건의 개수이며 성공 확률이나 시장가치가 아닙니다. 확인 가능한 조건 수가 적은 상품은 누락 지표를 먼저 확인하세요.",
    "없는 지표·빈 셀과 계산 불가 비율은 null이며 0으로 간주하지 않습니다. 전월에 없거나 기준 월에 사라진 상품은 후보에서 제외합니다.",
    "판매·광고 파일은 확인된 동일 쿠팡 옵션 ID만 연결합니다. 네이버 광고 소재 ID와 스마트스토어 상품 ID는 연결하지 않습니다.",
    "원가·재고·경쟁사 자료가 없어 실제 투자 우선순위, 시장성, 미래 매출이나 성과 원인은 확정할 수 없습니다.",
]


def _format(metric, value):
    if metric == "benchmark_roas":
        label, unit = "비교 상품 ROAS 중앙값", "%"
    else:
        base = metric.removesuffix("_change_pp").removesuffix("_change")
        label, unit = METRICS[base]
        if metric.endswith("_change_pp"):
            label, unit = label + " 증감", "%p"
        elif metric.endswith("_change"):
            label, unit = label + " 증감률", "%"
    number = f"{value:,.1f}".rstrip("0").rstrip(".")
    if metric.endswith(("_change", "_change_pp")) and value > 0:
        number = "+" + number
    return f"{label} {number}{unit}"


def create_diagnosis_insight(plan: ProductDiagnosisPlan, answer: Sequence[Mapping] | None) -> Insight:
    rows = list(answer or [])
    caller = {"plan": plan, "answer": rows}
    title = "기회 상품 후보" if plan.diagnosis_intent == "opportunity" else "관리 필요 상품"
    if not rows:
        particle = "가" if plan.diagnosis_intent == "opportunity" else "이"
        return Insight(status="ok", **caller, summary=f"비교 가능한 업로드 자료에서 요청 조건을 충족하는 {title}{particle} 없습니다.",
                       checks=["두 달의 상품별 자료와 누락 지표를 확인하세요."], limitations=LIMITATIONS)
    try:
        if len(rows) > plan.limit:
            raise ValueError("too many rows")
        for i, row in enumerate(rows, 1):
            if any(isinstance(v, (int, float)) and (isinstance(v, bool) or not math.isfinite(v)) for v in row.values()):
                raise ValueError("invalid number")
            rules = rule_results(row, plan.diagnosis_intent)
            reasons = [code for code, ok in rules.items() if ok is True]
            if (row["rank"] != i or row["diagnosis"] != plan.diagnosis_intent
                    or row["reason_codes"] != reasons or row["score"] != len(reasons) or not reasons
                    or row["evaluated_rules"] != sum(v is not None for v in rules.values())
                    or row["score_max"] != len(rules)
                    or row["previous_period"] != previous_calendar_month(row["period"])
                    or row["period"] != (plan.period or rows[0]["period"])
                    or not all(condition_matches(row, c) for c in plan.required_conditions)):
                raise ValueError("inconsistent diagnosis")
            if plan.diagnosis_intent == "opportunity" and not (rules["REVENUE_GROWTH"] and rules["SALES_VOLUME_GROWTH"]):
                raise ValueError("not an opportunity")
    except (KeyError, TypeError, ValueError):
        return Insight(status="unsupported_question", **caller, reason="inconsistent_diagnosis_results",
                       summary="상품 진단의 순위·점수·근거가 서로 맞지 않아 설명을 생성하지 않았습니다. 계산 결과를 확인해주세요.")
    evidence = []
    for row in rows:
        reasons = []
        for code in row["reason_codes"]:
            label, metrics = REASON_METRICS[code]
            values = ", ".join(_format(m, row[m]) for m in metrics if row[m] is not None)
            reasons.append(f"{label} ({values})")
        evidence.append(f"{row['rank']}위 · {entity(row)} · {row['previous_period']} → {row['period']} · "
                        f"확인된 신호 {row['score']}개 / 계산 가능한 조건 {row['evaluated_rules']}개: " + "; ".join(reasons) + ".")
    top = rows[0]
    return Insight(status="ok", **caller,
                   summary=f"{top['previous_period']} → {top['period']} 업로드 자료 기준 {title} {len(rows)}개입니다. "
                           f"1위는 {entity(top)}이며, 원자료의 변화 조건을 충족한 점검 후보입니다.",
                   evidence=evidence,
                   checks=["기준 월과 전월의 동일 상품 ID 및 빠진 판매·광고 자료를 확인하세요.",
                           "재고·마진·광고 소재·운영 가능 예산은 별도 자료로 확인하세요."],
                   actions=["후보의 원자료와 추가 확인 항목을 대조한 뒤 예산 또는 운영 변경 여부를 결정하세요."],
                   limitations=LIMITATIONS)
