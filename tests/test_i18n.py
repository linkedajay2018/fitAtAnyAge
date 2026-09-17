from fitafter40.core import config
from fitafter40.core.content import AGE_GUIDANCE, WORKOUT_PLANS


def test_default_locale_is_english(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b'lang="en"' in resp.data
    assert b"Workout Plans" in resp.data


def test_set_language_sets_cookie_and_redirects(client):
    resp = client.get("/set-language/hi")
    assert resp.status_code == 302
    assert resp.headers["Set-Cookie"].startswith("locale=hi")


def test_set_language_rejects_unsupported_code(client):
    resp = client.get("/set-language/xx")
    assert resp.status_code == 404


def test_hindi_cookie_renders_hindi_strings(client):
    client.set_cookie("locale", "hi")
    resp = client.get("/")
    assert resp.status_code == 200
    assert b'lang="hi"' in resp.data
    assert "वर्कआउट प्लान".encode() in resp.data


def test_language_switcher_present_on_every_page(client):
    for path in ("/", "/workouts", "/tools", "/safety", "/diet", "/membership", "/contact", "/login", "/signup"):
        resp = client.get(path)
        assert b"lang-select" in resp.data, path


def test_recommended_badge_uses_stable_level_id_not_translated_text(client):
    # The "Recommended for you" badge match (data-plan vs recommended_level)
    # must use WORKOUT_PLANS' stable level_id, not the translated level
    # text — otherwise switching locale silently breaks the match.
    client.set_cookie("locale", "hi")
    resp = client.get("/workouts")
    assert resp.status_code == 200
    data = resp.data.decode()
    for plan in WORKOUT_PLANS:
        assert f'data-plan="{plan["level_id"]}"' in data
        assert f'data-progress-for="{plan["level_id"]}"' in data
    for info in AGE_GUIDANCE.values():
        assert info["recommended_level"] in {p["level_id"] for p in WORKOUT_PLANS}


def test_diet_page_supplement_note_shown_in_hindi(client):
    client.set_cookie("locale", "hi")
    resp = client.get("/diet")
    assert resp.status_code == 200
    assert "सप्लीमेंट्स".encode() in resp.data


def test_chatbot_faq_matches_hindi_keywords(client):
    # Reply language follows the visitor's locale cookie, not the language
    # the question was typed in — Hindi keywords are matched so a
    # Hindi-locale visitor's question still finds the right FAQ entry.
    client.set_cookie("locale", "hi")
    resp = client.post("/chat", json={"message": "मुझे कितना पानी पीना चाहिए?"})
    assert resp.status_code == 200
    # jsonify() escapes non-ASCII as \uXXXX by default, so compare the
    # decoded reply rather than searching the raw response bytes.
    assert "लीटर" in resp.get_json()["reply"]


def test_translations_are_compiled():
    import os

    mo_path = os.path.join("translations", "hi", "LC_MESSAGES", "messages.mo")
    assert os.path.exists(mo_path), "Run `pybabel compile -d translations` after editing .po files"


def test_hindi_is_a_configured_language():
    assert "hi" in config.LANGUAGES
    assert config.DEFAULT_LOCALE == "en"
