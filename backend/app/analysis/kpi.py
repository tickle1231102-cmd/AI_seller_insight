"""담당: C — TECH_SPEC 5장 참고.

아래 함수 이름·시그니처는 B 의 routers/analyze.py 가 호출하는 계약이다. 본문은 C 가 구현한다.
"""


def compute_kpis(df) -> dict:
    """정규화 DataFrame → TECH_SPEC 7-4 의 kpis (period, previous_period, current, previous, change)."""
    raise NotImplementedError("C: compute_kpis 구현 필요")
