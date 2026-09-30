import pytest

from app.ai.conversation import create_small_talk_reply, small_talk_kind


@pytest.mark.parametrize("question, kind", [
    ("안녕!", "greeting"), ("하이~", "greeting"), ("hello", "greeting"),
    ("고마워요", "thanks"), ("감사합니다!", "thanks"),
    ("너 뭐 할 수 있어?", "help"), ("무엇을 물어볼 수 있나요?", "help"),
    ("어떻게 사용해?", "help"), ("넌 누구야?", "help"),
])
def test_small_talk_is_detected(question, kind):
    assert small_talk_kind(question) == kind


@pytest.mark.parametrize("question", [
    "안녕 매출 알려줘", "고마워, 근데 ROAS 는?", "최근 3개월 매출 합계",
    "왜 매출이 떨어졌어?", "광고비를 줄여야 할까?", "CTR 99%가 된 이유를 분석해줘",
    "뭐 할 수 있어? 쿠팡 광고비도 돼?", "오늘 날씨 어때?", "",
])
def test_data_or_other_questions_are_left_to_planner(question):
    assert small_talk_kind(question) is None
    assert create_small_talk_reply(question) is None


def test_reply_is_fixed_text_and_keeps_contract_status():
    reply = create_small_talk_reply("안녕!")
    assert reply.status == "unsupported_question" and reply.plan is None
    assert reply.summary.startswith("안녕하세요!")
    assert not any(ch.isdigit() for ch in reply.summary)
    assert reply.evidence == reply.checks == reply.actions == reply.limitations == []
    assert "방문수" not in reply.summary


def test_store_capabilities_only_when_store_file_uploaded():
    assert "방문수" in create_small_talk_reply("뭐 할 수 있어?", has_store=True).summary
