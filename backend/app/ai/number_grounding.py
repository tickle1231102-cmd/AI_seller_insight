"""Conservative display-number checks against deterministic analysis data.

This checks values and formatting, not complete semantic claim attribution.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any


_NUMBER_RE = re.compile(r"[-+−]?(?:\d+(?:,\d+)*(?:\.\d+)?|\.\d+)(?:[eE][-+]?\d+)?")
_PERIOD_RE = re.compile(r"(?<!\d)\d{4}-(?:0[1-9]|1[0-2])(?!\d)")
_KOREAN_PERIOD_RE = re.compile(r"(?<!\d)(\d{4})\s*년\s*(0?[1-9]|1[0-2])\s*월")
_MONEY_RE = re.compile(r"\s*(?:(천|만|억)\s*)?원")
_COMPOUND_MONEY_RE = re.compile(r"\d[\d,.]*\s*(?:천|만|억)\s*\d[\d,.]*\s*(?:천|만|억)?\s*원")
_PERCENT_RE = re.compile(r"\s*(%p|%|퍼센트포인트|퍼센트)")
_EDITORIAL_RE = re.compile(
    r"\s*(?:가지|개)\s*(?:의\s*)?(?:확인|점검|검토|행동|제안|권고|항목|단계|후보)"
)
_DOWN_AFTER_RE = re.compile(r"\s*(?:(?:가|이|만큼|정도)\s*)?(?:감소|하락|줄)")
_DOWN_BEFORE_RE = re.compile(r"(?:감소|하락)\s*(?:폭|율)?(?:은|는|이|가)?\s*$")
_MONEY_FIELDS = {"revenue", "ad_spend", "ad_revenue"}
_LABEL_FIELDS = {"product_id", "product_name", "platform", "signal"}
_EDITORIAL_FIELDS = {"checks", "actions", "limitations"}
_MONEY_MULTIPLIERS = {None: Decimal(1), "천": Decimal(1000),
                      "만": Decimal(10000), "억": Decimal(100000000)}


def _parse_number(token: str) -> Decimal:
    normalized = token.replace("−", "-")
    if "," in normalized and not re.fullmatch(
        r"[-+]?\d{1,3}(?:,\d{3})+(?:\.\d+)?(?:[eE][-+]?\d+)?", normalized
    ):
        raise ValueError("Invalid thousands grouping")
    number = Decimal(normalized.replace(",", ""))
    if not number.is_finite():
        raise ValueError("Non-finite number")
    return number


@dataclass
class NumberGrounding:
    numbers: set[Decimal] = field(default_factory=set)
    money: set[Decimal] = field(default_factory=set)
    percentages: set[Decimal] = field(default_factory=set)
    percentage_points: set[Decimal] = field(default_factory=set)
    changes: set[Decimal] = field(default_factory=set)
    periods: set[str] = field(default_factory=set)
    labels: set[str] = field(default_factory=set)
    answer_count: int = 0

    @classmethod
    def from_results(cls, *values: Any, answer_count: int = 0) -> NumberGrounding:
        context = cls(answer_count=answer_count)
        for value in values:
            context._collect(value)
        return context

    def _collect(self, value: Any, key: str = "") -> None:
        if isinstance(value, bool) or value is None:
            return
        if isinstance(value, Mapping):
            for name, nested in value.items():
                self._collect(nested, str(name))
            return
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            for nested in value:
                self._collect(nested, key)
            return
        if isinstance(value, str):
            if key in {"period", "previous_period"} and _PERIOD_RE.fullmatch(value):
                self.periods.add(value)
                return
            if key in _LABEL_FIELDS:
                # Digits inside known identifiers/names are not seller metrics.
                if any(char.isalpha() for char in value):
                    self.labels.add(value)
                return
            if not _NUMBER_RE.fullmatch(value):
                return
        elif not isinstance(value, (int, float, Decimal)):
            return
        try:
            number = _parse_number(str(value))
        except (InvalidOperation, ValueError):
            return
        self.numbers.add(number)
        if key in _MONEY_FIELDS:
            self.money.add(number)
        if key.endswith("_change_pp"):
            self.percentage_points.add(number)
            self.changes.add(number)
        elif key.endswith("_change"):
            self.percentages.add(number)
            self.changes.add(number)
        elif key in {"roas", "overall_roas"}:
            # C's contract already stores percentages, not fractional ratios.
            self.percentages.add(number)

    def matches(self, text: str, *, field_name: str) -> bool:
        # Mask only actual input periods and exact known labels. Dates must be
        # validated as pairs: knowing 2025-08 and 2026-09 doesn't allow 2025-09.
        masked = text
        for match in _PERIOD_RE.finditer(text):
            if match.group() not in self.periods:
                return False
            masked = _mask(masked, match.start(), match.end())
        for match in _KOREAN_PERIOD_RE.finditer(text):
            period = f"{match[1]}-{int(match[2]):02d}"
            if period not in self.periods:
                return False
            masked = _mask(masked, match.start(), match.end())
        for label in sorted(self.labels, key=len, reverse=True):
            pattern = rf"(?<![A-Za-z0-9]){re.escape(label)}(?![A-Za-z0-9])"
            masked = re.sub(pattern, lambda match: " " * len(match.group()), masked)

        # Only one exact currency scale is supported. Do not accidentally
        # validate the pieces of "1억 2,600만 원" as unrelated input values.
        if _COMPOUND_MONEY_RE.search(masked):
            return False

        for match in _NUMBER_RE.finditer(masked):
            try:
                number = _parse_number(match.group())
            except (InvalidOperation, ValueError):
                return False
            before, after = masked[:match.start()], masked[match.end():]
            unsigned_integer = (
                match.group().isdigit() and number == int(number) and number > 0
            )
            if re.match(r"\s*월", after):
                if not unsigned_integer or int(number) not in {int(p[5:]) for p in self.periods}:
                    return False
                continue
            if re.match(r"\s*년", after):
                if not unsigned_integer or int(number) not in {int(p[:4]) for p in self.periods}:
                    return False
                continue
            money = _MONEY_RE.match(after)
            if money:
                if number * _MONEY_MULTIPLIERS[money[1]] not in self.money:
                    return False
                continue
            percent = _PERCENT_RE.match(after)
            if percent:
                allowed = (self.percentage_points if percent[1] in {"%p", "퍼센트포인트"}
                           else self.percentages)
                # Unsigned "14.2%p 하락" can express an input change of -14.2.
                # Do not compare all values by absolute value: +17 and -17 are
                # different claims. Explicit signs must still match the data.
                explicit_sign = match.group().startswith(("+", "-", "−"))
                decreasing = (_DOWN_AFTER_RE.match(after[percent.end():])
                              or _DOWN_BEFORE_RE.search(before))
                expected = -number if decreasing and not explicit_sign else number
                if expected not in allowed:
                    return False
                if decreasing and not explicit_sign and expected not in self.changes:
                    return False
                continue
            if unsigned_integer:
                # A rank refers to returned rows, never to a sales count or the
                # requested plan.limit (which is not a source of metric values).
                rank = (re.search(r"(?:상위|하위)\s*$", before)
                        and re.match(r"\s*(?:개|위)(?![A-Za-z0-9])", after))
                ordinal = re.match(r"\s*순위", after)
                if (rank or ordinal) and int(number) <= self.answer_count:
                    continue
                # Only editorial lists/check-item counts get a small-number
                # exception. "판매량 3개" / "주문 2건" are still data claims.
                if field_name in _EDITORIAL_FIELDS and number <= 10:
                    line_prefix = before.rsplit("\n", 1)[-1]
                    list_marker = (not line_prefix.strip() and re.match(r"[.)]\s+", after))
                    if list_marker or _EDITORIAL_RE.match(after):
                        continue
            if number not in self.numbers:
                return False
        return True


def _mask(text: str, start: int, end: int) -> str:
    return text[:start] + " " * (end - start) + text[end:]
