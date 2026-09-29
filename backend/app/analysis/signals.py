"""담당: C — TECH_SPEC 6장 참고.

아래 함수 이름·시그니처는 B 의 routers/analyze.py 가 호출하는 계약이다. 본문은 C 가 구현한다.
"""


def detect_signals(kpis: dict, comparison: dict) -> list[dict]:
    """kpis·comparison → TECH_SPEC 6장 신호 목록 (각 항목에 signal, platform 포함)."""
    raise NotImplementedError("C: detect_signals 구현 필요")
