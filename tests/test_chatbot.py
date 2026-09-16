from unittest.mock import patch

import config
from chatbot import get_faq_reply
from content import CHATBOT_FAQ


def test_faq_knowledge_base_is_well_formed():
    assert len(CHATBOT_FAQ) >= 10
    for entry in CHATBOT_FAQ:
        assert entry["keywords"]
        assert entry["answer"]


def test_get_faq_reply_matches_protein_question():
    reply = get_faq_reply("How much protein do I need?")
    assert "protein" in reply.lower()


def test_get_faq_reply_matches_hydration_question():
    reply = get_faq_reply("How much water should I drink?")
    assert "water" in reply.lower() or "hydrat" in reply.lower()


def test_get_faq_reply_matches_protein_powder_question():
    reply = get_faq_reply("Should I take whey protein powder?")
    assert "protein" in reply.lower()


def test_get_faq_reply_falls_back_for_unmatched_question():
    reply = get_faq_reply("What's the airspeed velocity of an unladen swallow?")
    assert "don't have a specific answer" in reply.lower()


def test_get_faq_reply_handles_empty_message():
    reply = get_faq_reply("")
    assert reply


def test_chat_endpoint_uses_faq_by_default(client):
    resp = client.post("/chat", json={"message": "How much protein do I need?"})
    assert resp.status_code == 200
    assert "protein" in resp.get_json()["reply"].lower()


def test_chat_endpoint_handles_empty_message(client):
    resp = client.post("/chat", json={"message": ""})
    assert resp.status_code == 200
    assert resp.get_json()["reply"]


def test_chat_endpoint_uses_ai_when_configured(client, monkeypatch):
    monkeypatch.setattr(config, "CHATBOT_AI_CONFIGURED", True)

    with patch("app.get_ai_reply", return_value="AI generated answer") as mock_ai:
        resp = client.post("/chat", json={"message": "hello"})

    assert resp.status_code == 200
    assert resp.get_json()["reply"] == "AI generated answer"
    mock_ai.assert_called_once()


def test_chat_endpoint_falls_back_to_faq_when_ai_errors(client, monkeypatch):
    monkeypatch.setattr(config, "CHATBOT_AI_CONFIGURED", True)

    with patch("app.get_ai_reply", side_effect=Exception("API down")):
        resp = client.post("/chat", json={"message": "How much protein do I need?"})

    assert resp.status_code == 200
    assert "protein" in resp.get_json()["reply"].lower()


def test_chat_widget_appears_on_every_page(client):
    for path in ("/", "/workouts", "/diet", "/tools", "/safety"):
        resp = client.get(path)
        assert b"chat-widget" in resp.data, path
