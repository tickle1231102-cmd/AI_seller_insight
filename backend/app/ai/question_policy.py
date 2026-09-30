"""Conservative checks for conditions the existing AnalysisPlan can represent."""
from dataclasses import dataclass, field
import re

from .models import AnalysisPlan


@dataclass
class Requirements:
    expected: dict = field(default_factory=dict)
    reason: str | None = None


def inspect_question(question: str, *, periods: list[str] | None = None) -> Requirements:
    q = question.lower()
    r = Requirements()
    def block(message):
        r.reason = message
        return r
    if re.search(r"순이익|이익률|마진|원가|수수료|재고|ctr|cpc|cvr|경쟁사|날씨|시장점유", q):
        return block("요청한 지표는 현재 지원 데이터로 계산할 수 없습니다. 기본 판매·광고 지표 또는 스마트스토어 판매 분석 지표로 질문해 주세요.")
    if re.search(r"상반기|하반기|분기|주별|일별|연간|올해|작년|어제|오늘|최근|부터|까지|원인|왜|때문|영향|소재별", q):
        return block("요청한 기간 범위·변화량·원인 조건을 현재 분석 계획으로 표현할 수 없습니다. YYYY-MM 한 달 또는 월별 지표 조회로 질문해 주세요.")
    if re.search(r"\d+\s*개월", q):
        return block("개월 수로 지정한 기간 범위는 현재 분석 계획으로 표현할 수 없습니다. YYYY-MM 한 달 또는 기간 지정 없이 월별로 질문해 주세요.")
    platforms = set(re.findall(r"쿠팡|네이버|coupang|naver", q))
    canonical = {"coupang" if p in {"쿠팡", "coupang"} else "naver" for p in platforms}
    if len(canonical) == 1 or re.search(r"(?<![a-z0-9])p\d{3,}(?![0-9])|상품\s*['\"‘“]|카테고리|지역별|고객별|성별|연령", q):
        return block("특정 플랫폼·상품의 필터 조건 또는 해당 분류는 아직 지원하지 않습니다. 플랫폼별·상품별·월별 전체 비교로 질문해 주세요.")
    dates = re.findall(r"(?<!\d)(\d{4})(?:-\s*|년\s*)(\d{1,2})(?:월)?(?!\d)", q)
    if len(dates) > 1 or any(not 1 <= int(m) <= 12 for _, m in dates):
        return block("한 번에 유효한 YYYY-MM 한 달을 지정하거나 기간 지정 없이 월별로 질문해 주세요.")
    stripped_dates = re.sub(r"\d{4}(?:-\s*|년\s*)\d{1,2}월?", "", q)
    available = sorted(set(p for p in periods or [] if re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", p)))
    months = re.findall(r"(?<!\d)(\d{1,2})\s*월", stripped_dates)
    relative = re.findall(r"이번\s*달|지난\s*달|전월(?!\s*대비)", stripped_dates)
    if len(dates) + len(months) + len(relative) > 1 or re.search(r"\d{4}\s*년", stripped_dates):
        return block("한 번에 한 달만 지정할 수 있습니다. YYYY-MM으로 명확하게 질문해 주세요.")
    selected = f"{dates[0][0]}-{int(dates[0][1]):02d}" if dates else None
    if months or relative:
        if not available:
            return block("월 표현을 해석할 업로드 기간이 없습니다. 연도와 월을 YYYY-MM으로 지정해 주세요.")
        if months:
            month = int(months[0])
            if not 1 <= month <= 12:
                return block("유효한 월을 지정해 주세요.")
            matching = [p for p in available if int(p[-2:]) == month]
            if len(matching) > 1:
                return block("같은 월이 여러 연도에 있습니다. YYYY-MM으로 지정해 주세요.")
            selected = matching[0] if matching else f"{available[-1][:4]}-{month:02d}"
        elif relative[0].replace(" ", "") == "이번달":
            selected = available[-1]
        else:
            year, month = map(int, available[-1].split("-"))
            selected = f"{year - 1}-12" if month == 1 else f"{year}-{month - 1:02d}"
    r.expected["period"] = selected
    metrics = []
    rest = q
    for metric, pattern in (
        ("gross_revenue", r"총\s*매출|판매\s*금액\s*\(\s*총\s*\)"),
        ("ad_revenue", r"광고\s*(?:전환)?\s*매출|전환\s*매출"),
        ("ad_spend", r"광고\s*비용|광고\s*비(?!교)"),
        ("roas", r"roas|광고\s*(?:수익률|효율)"),
        ("visits", r"방문\s*(?:수|자)|visits"),
        ("aov", r"객단가|결제\s*단가|aov"),
        ("conversion_rate", r"(?:구매\s*)?전환\s*율"),
        ("refund_rate", r"환불\s*률"),
        ("discount_rate", r"할인\s*율"),
        ("orders", r"상품\s*결제\s*건수|주문|결제\s*건수"),
        ("units", r"결제\s*상품\s*수량|판매\s*수량|판매량"),
        ("revenue", r"판매\s*금액\s*\(\s*순\s*\)|순\s*매출|매출"),
    ):
        if re.search(pattern, rest):
            metrics.append(metric)
            rest = re.sub(pattern, "", rest)
    if len(metrics) > 1:
        return block("한 번의 질문에서는 지표 하나만 조회할 수 있습니다. 비교할 지표를 하나씩 지정해 주세요.")
    if metrics:
        metric = metrics[0]
        if re.search(r"전월\s*대비|증감|증가율|감소율|하락폭|늘어난|증가한|줄어든|감소한|성장한", q):
            metric += "_change_pp" if metric in {"roas", "conversion_rate", "refund_rate", "discount_rate"} else "_change"
        r.expected["metric"] = metric
    elif re.search(r"잘\s*팔|잘되|좋은|안\s*좋은|나쁜|성적|성과", q):
        return block("판단 기준이 모호합니다. 매출·주문 수·판매 수량·ROAS 중 기준을 지정해 주세요.")
    groups = [g for g, p in (("product", r"상품"), ("period", r"월별|기간별|추이"),
                              ("platform", r"플랫폼|쿠팡|네이버|coupang|naver")) if re.search(p, rest)]
    if len(groups) > 1:
        return block("한 번에 분류 하나만 지원합니다. 상품별·플랫폼별·월별 중 하나를 선택해 주세요.")
    r.expected["group_by"] = groups[0] if groups else None
    if r.expected.get("metric", "").endswith(("_change", "_change_pp")) and r.expected["group_by"] == "period":
        return block("전월 대비 증감은 월별로 묶을 수 없습니다. 상품별·플랫폼별 증감 또는 월별 기본 지표 추이로 질문해 주세요.")
    if re.search(r"낮|적은|안\s*좋|최저|하위|적게|줄어든|감소한", rest):
        r.expected["sort"] = "asc"
    elif re.search(r"높|많|좋|최고|상위|큰|늘어난|증가한", rest):
        r.expected["sort"] = "desc"
    counts = re.findall(r"(?:상위|하위|top)\s*(\d+)|(?<!\d)(\d+)\s*개(?!월)", stripped_dates)
    if counts:
        values = {int(a or b) for a, b in counts}
        if len(values) != 1 or not 1 <= next(iter(values)) <= 50:
            return block("조회 개수는 1~50개 범위에서 하나로 지정해 주세요.")
        r.expected["limit"] = values.pop()
    return r


def plan_mismatch(requirements: Requirements, plan: AnalysisPlan) -> str | None:
    for key, value in requirements.expected.items():
        if getattr(plan, key) != value:
            labels = {"metric": "지표", "group_by": "분류", "period": "기간", "sort": "정렬", "limit": "개수"}
            return f"질문의 {labels[key]} 조건과 분석 계획이 일치하지 않아 실행하지 않았습니다. 조건을 명확히 지정해 다시 질문해 주세요."
    return None
