from unittest.mock import patch

import app as app_module
import config
from models import ContactMessage, db

from helpers import signup


def test_admin_search_filters_by_email(client, monkeypatch):
    monkeypatch.setattr(config, "ADMIN_EMAILS", {"boss@example.com"})
    with patch("app.send_verification_email"):
        signup(client, email="alice@example.com")
        client.get("/logout")
        signup(client, email="bob@example.com")
        client.get("/logout")
        signup(client, email="boss@example.com")

    resp = client.get("/admin?q=alice")
    assert resp.status_code == 200
    assert b"alice@example.com" in resp.data
    assert b"bob@example.com" not in resp.data


def test_admin_search_is_case_insensitive(client, monkeypatch):
    monkeypatch.setattr(config, "ADMIN_EMAILS", {"boss@example.com"})
    with patch("app.send_verification_email"):
        signup(client, email="alice@example.com")
        client.get("/logout")
        signup(client, email="boss@example.com")

    resp = client.get("/admin?q=ALICE")
    assert resp.status_code == 200
    assert b"alice@example.com" in resp.data


def test_admin_search_no_match_shows_empty_state(client, monkeypatch):
    monkeypatch.setattr(config, "ADMIN_EMAILS", {"boss@example.com"})
    with patch("app.send_verification_email"):
        signup(client, email="boss@example.com")

    resp = client.get("/admin?q=nobody-matches-this")
    assert resp.status_code == 200
    assert b"No users match" in resp.data


def test_admin_messages_requires_admin(client):
    resp = client.get("/admin/messages")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_admin_messages_forbidden_for_regular_user(client):
    with patch("app.send_verification_email"):
        signup(client)
    resp = client.get("/admin/messages")
    assert resp.status_code == 403


def test_admin_messages_lists_contact_submissions(client, monkeypatch):
    monkeypatch.setattr(config, "ADMIN_EMAILS", {"boss@example.com"})
    client.post(
        "/contact",
        data={"name": "Casey", "email": "casey@example.com", "message": "Need help with my plan"},
        follow_redirects=True,
    )
    with patch("app.send_verification_email"):
        signup(client, email="boss@example.com")

    resp = client.get("/admin/messages")
    assert resp.status_code == 200
    assert b"Casey" in resp.data
    assert b"casey@example.com" in resp.data
    assert b"Need help with my plan" in resp.data


def test_admin_can_mark_message_read_and_unread(client, monkeypatch):
    monkeypatch.setattr(config, "ADMIN_EMAILS", {"boss@example.com"})
    client.post(
        "/contact",
        data={"name": "Casey", "email": "casey@example.com", "message": "Hi"},
        follow_redirects=True,
    )
    with patch("app.send_verification_email"):
        signup(client, email="boss@example.com")

    with app_module.app.app_context():
        msg = ContactMessage.query.filter_by(email="casey@example.com").first()
        msg_id = msg.id
        assert msg.is_read is False

    client.post(f"/admin/messages/{msg_id}/toggle-read", follow_redirects=True)
    with app_module.app.app_context():
        assert db.session.get(ContactMessage, msg_id).is_read is True

    client.post(f"/admin/messages/{msg_id}/toggle-read", follow_redirects=True)
    with app_module.app.app_context():
        assert db.session.get(ContactMessage, msg_id).is_read is False


def test_admin_can_delete_message(client, monkeypatch):
    monkeypatch.setattr(config, "ADMIN_EMAILS", {"boss@example.com"})
    client.post(
        "/contact",
        data={"name": "Casey", "email": "casey@example.com", "message": "Hi"},
        follow_redirects=True,
    )
    with patch("app.send_verification_email"):
        signup(client, email="boss@example.com")

    with app_module.app.app_context():
        msg_id = ContactMessage.query.filter_by(email="casey@example.com").first().id

    resp = client.post(f"/admin/messages/{msg_id}/delete", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Message deleted" in resp.data

    with app_module.app.app_context():
        assert db.session.get(ContactMessage, msg_id) is None


def test_admin_page_shows_unread_message_count(client, monkeypatch):
    monkeypatch.setattr(config, "ADMIN_EMAILS", {"boss@example.com"})
    client.post(
        "/contact",
        data={"name": "Casey", "email": "casey@example.com", "message": "Hi"},
        follow_redirects=True,
    )
    with patch("app.send_verification_email"):
        signup(client, email="boss@example.com")

    resp = client.get("/admin")
    assert resp.status_code == 200
    assert b">1<" in resp.data
