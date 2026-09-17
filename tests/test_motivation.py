from fitAtAnyAge.core.content import MOTIVATIONAL_QUOTES


def test_motivational_quotes_list_is_populated():
    # Entries are flask_babel LazyStrings (translatable), not plain str —
    # str() them before checking content.
    assert len(MOTIVATIONAL_QUOTES) >= 10
    assert all(str(q).strip() for q in MOTIVATIONAL_QUOTES)


def test_homepage_shows_a_motivation_banner(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"motivation-banner" in resp.data
    assert b"motivation-quotes-data" in resp.data
    assert any(quote.encode() in resp.data for quote in MOTIVATIONAL_QUOTES)


def test_motivation_banner_appears_on_every_page(client):
    for path in ("/", "/workouts", "/tools", "/safety", "/membership", "/contact", "/login", "/signup"):
        resp = client.get(path)
        assert b"motivation-banner" in resp.data, path


def test_motivation_banner_appears_on_404_page(client):
    resp = client.get("/this-does-not-exist")
    assert resp.status_code == 404
    assert b"motivation-banner" in resp.data
