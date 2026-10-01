"""Recognize a bounded set of composite questions without dropping constraints."""
from __future__ import annotations

import re

from .models import PlannerResult, ProductDiagnosisPlan
from .question_policy import inspect_question

# Specific compound conditions are consumed before the general intent words.
PHRASES = (
    (r"주목(?:하고|해서|하며)\s*관리(?:해야\s*할|할|가\s*필요한)?", "attention", ()),
    (r"광고\s*비(?:는|가)?\s*(?:늘었|증가했)(?:는데|지만|고)\s*(?:광고\s*매출|성과)(?:는|가)?\s*(?:떨어진|떨어지는|감소한|나빠진|나빠지는)", "attention", ("ad_spend_up", "ad_revenue_down")),
    (r"광고\s*비(?:는|가)?\s*(?:늘었|증가했)(?:는데|지만|고)\s*(?:광고\s*매출|성과)(?:는|가)?\s*(?:안\s*나는|부진한|늘지\s*않는)", "attention", ("ad_spend_up", "ad_revenue_not_up")),
    (r"(?:판매|매출)(?:는|은|이|가)?\s*(?:오르|늘|증가하)(?:는데|지만|고)\s*광고(?:비)?(?:를|는|가)?\s*덜\s*(?:쓰고\s*있는|쓰는|쓴)", "opportunity", ("revenue_up", "ad_spend_down")),
    (r"광고\s*비\s*대비\s*성과(?:가|는)?\s*(?:안\s*좋아지는|떨어지는|나빠지는)", "attention", ("roas_down",)),
    (r"광고\s*효율(?:이|은|가)?\s*(?:떨어지는|나빠지는|안\s*좋아지는|하락한)", "attention", ("roas_down",)),
    (r"저평가(?:된|되어\s*있는)?", "opportunity", ()),
    (r"기회(?:가\s*있는)?", "opportunity", ()),
    (r"주목(?:해야\s*할|할\s*만한|할|해\s*볼|해볼)?", "opportunity", ()),
    (r"성장\s*가능성(?:이\s*높은|이\s*있는|\s*있는)?", "opportunity", ()),
    (r"더\s*키워\s*볼(?:\s*만한)?", "opportunity", ()),
    (r"광고(?:를)?\s*더\s*붙여\s*볼(?:\s*만한)?", "opportunity", ()),
    (r"잘\s*크고\s*있는", "opportunity", ()),
    (r"관리(?:가?\s*필요한|\s*필요|해야\s*할|할)", "attention", ()),
    (r"주의(?:가\s*필요한|해야\s*할|할|\s*필요)?", "attention", ()),
    (r"성과(?:가|는)?\s*(?:나빠지고\s*있는|나빠지는|떨어지고\s*있는|떨어지는|떨어진|꺾인)", "attention", ()),
    (r"꺾이는", "attention", ()),
)
PERIOD_TOKEN = re.compile(r"(?<!\d)\d{4}(?:-\s*|년\s*)\d{1,2}월?(?!\d)|(?<!\d)\d{1,2}\s*월|이번\s*달|지난\s*달|전월(?!\s*대비)")
COUNT_TOKEN = re.compile(r"(?:상위|top)\s*\d+|(?<!\d)\d+\s*개(?!월)")
UNSUPPORTED = re.compile(r"경쟁사|시장|마진|원가|이익|수수료|재고|소재|ctr|cpc|cvr|왜|원인|때문|예측|미래|다음\s*달|내년|\d+\s*개월|상반기|하반기|분기|주별|일별|부터|까지", re.I)


def diagnosis_plan(question: str, *, periods: list[str] | None = None) -> PlannerResult | None:
    q = question.strip().lower()
    remaining = q
    intents, conditions = set(), set()
    for pattern, intent, required in PHRASES:
        if re.search(pattern, remaining):
            remaining = re.sub(pattern, " ", remaining)
            intents.add(intent)
            conditions.update(required)
    if not intents:
        return None
    def reject(reason):
        return PlannerResult(status="unsupported_question", reason=reason)
    if UNSUPPORTED.search(q):
        return reject("상품 진단은 업로드된 최신월(또는 지정한 월)과 전월의 판매·광고 자료로만 계산합니다. 경쟁사·마진·재고·미래 예측·성과 원인은 판단하지 않습니다.")
    if len(intents) != 1:
        return reject("기회 상품 후보와 관리 필요 상품은 한 번에 하나씩 질문해주세요.")
    if not re.search(r"상품", q):
        return reject("복합 진단은 상품별로 지원합니다. '기회 상품 후보' 또는 '관리할 상품'으로 질문해주세요.")
    # Resolve dates/top-N with the existing, tested calendar rules. Recent/now
    # means the latest uploaded month only in this dedicated diagnosis branch.
    period_tokens = PERIOD_TOKEN.findall(remaining)
    without_periods = PERIOD_TOKEN.sub(" ", remaining)
    count_tokens = COUNT_TOKEN.findall(without_periods)
    requirements = inspect_question("매출 " + " ".join(period_tokens + count_tokens), periods=periods)
    if requirements.reason:
        return reject(requirements.reason)
    remaining = COUNT_TOKEN.sub(" ", without_periods)
    remaining = re.sub(r"판매\s*추세로\s*볼\s*때|전월\s*대비|최신\s*월|최근|지금|현재", " ", remaining)
    remaining = re.sub(r"상품(?:들)?|후보|알려\s*줘(?:요)?|알려\s*주세요|보여\s*줘(?:요)?|보여\s*주세요|추천해\s*줘(?:요)?|추천|찾아\s*줘(?:요)?|어떤|무엇|뭐|있을까|있나요|있어|인가요|인가는|순위|목록", " ", remaining)
    remaining = re.sub(r"(?:은|는|을|를|이|가|의|중|좀|요|야|해줘)|[\s?!.,:~]", "", remaining)
    if remaining:
        return reject("질문에 상품 진단으로 표현할 수 없는 조건이 있습니다. 특정 상품·플랫폼 필터나 별도 조건을 빼지 않고 안내합니다. '관리할 상품 3개'처럼 질문해주세요.")
    return PlannerResult(status="ok", plan=ProductDiagnosisPlan(
        diagnosis_intent=next(iter(intents)), period=requirements.expected["period"],
        limit=requirements.expected.get("limit", 5), required_conditions=sorted(conditions)))
