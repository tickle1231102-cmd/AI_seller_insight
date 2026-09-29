"""PR #10 A-review regressions: formatting exceptions must not invent metrics."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal

import pytest

from backend.app.ai.insight import create_insight
from backend.app.ai.models import AnalysisPlan, InsightContent
from backend.app.ai.number_grounding import NumberGrounding


KPI = {
    "period": "2026-09",
    "previous_period": "2026-08",
    "current": {"revenue": 12600000, "orders": 42, "roas": 312.5},
    "change": {"revenue_change": -17.0, "ad_spend_change": 28.0,
               "roas_change_pp": -14.2},
}
ANSWER = [{"product_id": f"P00{i}", "product_name": f"상품 {i}", "revenue": 4200000}
          for i in range(1, 4)]
PLAN = AnalysisPlan(metric="revenue", group_by="product", limit=3)
FIELDS = ["summary", "evidence", "checks", "actions", "limitations"]


class FakeLLM:
    def __init__(self, result):
        self.result = result

    def generate_structured(self, **kwargs):
        return self.result


def run(text, *, field="summary", kpis=None, answer=None):
    result = InsightContent(summary="업로드된 데이터로 확인하세요.", evidence=[],
                            checks=[], actions=[], limitations=[])
    result = result.model_copy(update={field: text if field == "summary" else [text]})
    return create_insight(KPI if kpis is None else kpis, {}, [],
                          plan=PLAN if answer is not None else None,
                          answer=answer, llm=FakeLLM(result))


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("text", [
    "9월 매출은 12,600,000원입니다.",
    "2026-09 매출은 1,260만 원입니다.",
    "2026년 9월 매출은 0.126억 원입니다.",
    "8월과 9월 수치를 확인하세요.",
    "매출 1.26e7원, ROAS 312.5%입니다.",
    "매출이 17% 감소하고 ROAS가 14.2%p 하락했습니다.",
    "ROAS 하락 폭은 14.2%p입니다.",
])
def test_input_dates_exact_units_and_unsigned_decreases_are_valid_in_every_field(field, text):
    result = run(text, field=field)
    assert result.status == "ok"
    assert getattr(result, field) == (text if field == "summary" else [text])


@pytest.mark.parametrize("field", ["checks", "actions", "limitations"])
@pytest.mark.parametrize("text", [
    "1. 플랫폼별 광고비를 확인하세요.",
    "2가지 확인 사항을 점검하세요.",
    "3개 항목을 검토하세요.",
    "1) 광고비 확인\n2) 추가 데이터 확인",
])
def test_small_editorial_counts_and_list_markers_are_not_sales_claims(field, text):
    assert run(text, field=field).status == "ok"


@pytest.mark.parametrize("text", ["상위 3개 상품을 확인하세요.", "3순위 상품 P003을 확인하세요."])
def test_rank_count_is_grounded_in_returned_rows(text):
    result = run(text, answer=ANSWER)
    assert result.status == "ok"
    assert result.plan == PLAN and result.answer == ANSWER


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("text", [
    "10월 매출입니다.",
    "2027년 매출입니다.",
    "2026-10 매출입니다.",
    "매출 1,261만 원입니다.",
    "ROAS 31250%입니다.",
    "ROAS +14.2%p입니다.",
    "광고비 -28%입니다.",
    "판매량 3개입니다.",
    "주문 2건입니다.",
    "매출 12,60,000원입니다.",
])
def test_false_positive_exceptions_do_not_allow_fabricated_data(field, text):
    result = run(text, field=field)
    if field == "evidence":
        assert result.status == "ok"
        assert result.evidence == []
    else:
        assert result.status == "llm_error"
        assert result.reason == "ungrounded_insight_number"


def test_year_and_month_cannot_be_recombined_into_an_unknown_period():
    kpis = {"period": "2026-09", "previous_period": "2025-08"}
    assert run("2025-09 매출입니다.", kpis=kpis).status == "llm_error"
    assert run("2025년 9월 매출입니다.", kpis=kpis).status == "llm_error"


@pytest.mark.parametrize("text", ["상위 4개 상품", "4순위 상품", "상위 3개 상품"])
def test_rank_cannot_exceed_actual_answer_count_or_use_plan_limit(text):
    answer = ANSWER if "4" in text else ANSWER[:1]
    result = run(text, answer=answer)
    assert result.status == "llm_error"
    assert result.plan == PLAN and result.answer == answer


def test_period_parts_and_identifier_digits_are_not_generic_metric_sources():
    context = NumberGrounding.from_results({"period": "2026-09", "product_id": "P003"})
    assert context.numbers == set()
    assert context.matches("9월", field_name="summary")
    assert context.matches("상품 P003", field_name="summary")
    assert not context.matches("매출 9원", field_name="summary")
    assert not context.matches("판매량 3개", field_name="summary")


def test_c_contract_percentages_are_not_fractional_ratios():
    kpis = {"current": {"roas": 0.123}, "change": {"revenue_change": -0.123}}
    assert run("ROAS 0.123%", kpis=kpis).status == "ok"
    assert run("매출 0.123% 감소", kpis=kpis).status == "ok"
    assert run("ROAS 12.3%", kpis=kpis).status == "llm_error"


def test_known_identifiers_and_boolean_flags_cannot_supply_sale_counts():
    context = NumberGrounding.from_results({"product_id": "P003", "enabled": True})
    assert context.numbers == set()
    assert not context.matches("주문 1건", field_name="summary")


def test_month_and_money_exceptions_preserve_original_plan_answer_and_data():
    kpis = deepcopy(KPI)
    answer = deepcopy(ANSWER)
    result = run("9월 매출 1,260만 원, 상위 3개 상품을 확인하세요.",
                 kpis=kpis, answer=answer)
    assert result.status == "ok"
    assert result.plan == PLAN and result.answer == ANSWER
    assert kpis == KPI and answer == ANSWER


def test_exact_decimal_currency_conversion_does_not_round():
    context = NumberGrounding.from_results({"revenue": 12600001})
    assert context.money == {Decimal("12600001")}
    assert context.matches("매출 1260.0001만 원", field_name="summary")
    assert not context.matches("매출 1260만 원", field_name="summary")


def test_unsupported_compound_currency_cannot_validate_as_separate_numbers():
    context = NumberGrounding.from_results({"orders": 1, "revenue": 26000000})
    assert not context.matches("매출 1억 2,600만 원", field_name="summary")
