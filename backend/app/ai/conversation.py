"""Server-fixed replies for greetings and "what can you do?" messages.

These messages are not analysis questions, so they skip the planner LLM call
and get a friendly fixed reply instead of the generic rejection. Status stays
unsupported_question (no analysis plan), so the response contract is unchanged.
Anything that mentions data (지표·플랫폼·상품·기간) is left to the planner.
"""
from __future__ import annotations

import re

from .models import Insight

DATA_WORDS = re.compile(
    r"매출|주문|판매|수량|광고|roas|로아스|상품|플랫폼|네이버|쿠팡|스토어|방문|전환|환불|할인|객단가|"
    r"결제|비용|수익|성과|효율|\d|월|주|분기|년|지난|이번|최근|왜|이유|원인",
    re.IGNORECASE)
GREETING = re.compile(r"^(안녕|하이|헬로|hello|hi|hey|반가|좋은 ?(아침|하루|저녁))", re.IGNORECASE)
THANKS = re.compile(r"(고마|감사|thank|땡큐)", re.IGNORECASE)
HELP = re.compile(
    r"(뭐|무엇|무슨|어떤).{0,6}(할 ?수|해 ?줄 ?수|가능|기능|물어|질문)|"
    r"(어떻게|어케).{0,4}(써|사용|쓰)|사용법|도움말|help|(너|넌|당신).{0,3}(누구|뭐야|뭐니)",
    re.IGNORECASE)

CAPABILITIES = (
    "업로드하신 자료로 매출·주문 수·판매 수량·광고비·광고 전환매출·ROAS를 "
    "플랫폼별·상품별·월별로 비교하고, 전월 대비 얼마나 늘거나 줄었는지 알려드릴 수 있어요."
)
STORE_CAPABILITIES = " 스마트스토어 판매 분석 파일이 있으면 방문수·구매전환율·환불률도 볼 수 있어요."
COUPANG_CAPABILITIES = " 쿠팡 판매 분석 파일이 있으면 쿠팡 방문자·구매전환율·장바구니율·취소율도 볼 수 있어요."
REPLIES = {
    "greeting": "안녕하세요! 판매·광고 데이터를 함께 살펴보는 AI 어시스턴트예요. ",
    "thanks": "도움이 되었다니 다행이에요. 더 궁금한 점이 있으면 편하게 물어봐 주세요. ",
    "help": "",
}


def small_talk_kind(question: str) -> str | None:
    text = question.strip()
    if not text or len(text) > 40 or DATA_WORDS.search(text):
        return None
    if HELP.search(text):
        return "help"
    if GREETING.search(text):
        return "greeting"
    if THANKS.search(text):
        return "thanks"
    return None


def create_small_talk_reply(question: str, *, has_store: bool = False, has_coupang_sales: bool = False) -> Insight | None:
    """Fixed reply for greeting/thanks/help messages, or None for everything else."""
    kind = small_talk_kind(question)
    if kind is None:
        return None
    capabilities = (CAPABILITIES + (STORE_CAPABILITIES if has_store else "")
                    + (COUPANG_CAPABILITIES if has_coupang_sales else ""))
    return Insight(status="unsupported_question", summary=REPLIES[kind] + capabilities)
