"""담당: C — TECH_SPEC 5장 참고.

아래 함수 이름·시그니처는 B 의 routers/analyze.py 가 호출하는 계약이다. 본문은 C 가 구현한다.
"""


def build_comparison(df) -> dict:
    """정규화 DataFrame → TECH_SPEC 7-4 의 comparison (by_platform, trend)."""
    raise NotImplementedError("C: build_comparison 구현 필요")


def run_plan(df, plan) -> list[dict]:
    """D 의 AnalysisPlan (metric, group_by, sort, limit, period) 을 실행 → insight.answer 행 목록."""
    raise NotImplementedError("C: run_plan 구현 필요")
