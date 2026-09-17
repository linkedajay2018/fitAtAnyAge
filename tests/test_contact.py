from fitAtAnyAge import app as app_module
from fitAtAnyAge.core.models import ContactMessage


def test_contact_get(client):
    resp = client.get("/contact")
    assert resp.status_code == 200


def test_contact_post_valid_shows_thanks_message(client):
    resp = client.post(
        "/contact",
        data={"name": "Alex", "email": "alex@example.com", "message": "Hi there"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Thanks Alex" in resp.data


def test_contact_post_missing_fields_shows_error(client):
    resp = client.post(
        "/contact",
        data={"name": "", "email": "", "message": ""},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Please fill in both" in resp.data


def test_contact_post_invalid_email_shows_error(client):
    resp = client.post(
        "/contact",
        data={"name": "Alex", "email": "not-an-email", "message": "Hi there"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Enter a valid email address" in resp.data


def test_contact_post_persists_message(client):
    client.post(
        "/contact",
        data={"name": "Jordan", "email": "jordan@example.com", "message": "Persisted?"},
        follow_redirects=True,
    )
    with app_module.app.app_context():
        saved = ContactMessage.query.filter_by(email="jordan@example.com").first()
        assert saved is not None
        assert saved.name == "Jordan"
        assert saved.message == "Persisted?"
        assert saved.is_read is False
