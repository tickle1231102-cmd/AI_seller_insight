from types import SimpleNamespace

from app.ai.client import LLMClientError
from app.ai.conversation import ConversationReply, create_conversation_reply

KPIS = {"period": "2026-08", "current": {"revenue": 3800000, "roas": 312.5}}


class FakeLLM:
    def __init__(self, reply=None, error=None):
        self.reply, self.error, self.calls = reply, error, []

    def generate_structured(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.reply


def reply(text, suggestions=("매출 상위 3개 상품 알려줘",)):
    return ConversationReply(reply=text, suggested_questions=list(suggestions))


def test_natural_reply_uses_only_input_numbers():
    llm = FakeLLM(reply("8월 매출은 3,800,000원이고 ROAS는 312.5%예요. 원인은 노출·클릭 데이터로 확인해야 해요."))
    result = create_conversation_reply("왜 매출이 이래?", KPIS, {}, [], reason="원인 데이터 없음", llm=llm)
    assert result.status == "ok" and "3,800,000" in result.summary
    assert result.actions == ["이렇게 물어볼 수 있어요: “매출 상위 3개 상품 알려줘”"]
    assert result.limitations == ["원인 데이터 없음"]
    assert "왜 매출이 이래?" in llm.calls[0]["input_text"]


def test_invented_number_falls_back():
    llm = FakeLLM(reply("매출이 25% 늘 거예요."))
    assert create_conversation_reply("앞으로 어때?", KPIS, {}, [], llm=llm) is None


def test_question_numbers_may_be_repeated():
    llm = FakeLLM(reply("7개는 어렵지만 상위 상품은 볼 수 있어요."))
    assert create_conversation_reply("7개 비교해줘", KPIS, {}, [], llm=llm) is not None


def test_llm_error_falls_back():
    llm = FakeLLM(error=LLMClientError("timeout", "x"))
    assert create_conversation_reply("안녕", KPIS, {}, [], llm=llm) is None
