from fitafter40 import app as app_module
from fitafter40.core import config
from fitafter40.core.models import User, db

from helpers import login, signup


def test_signup_creates_user_and_logs_in(client):
    resp = signup(client)
    assert resp.status_code == 200
    assert b"Welcome to FitAtAnyAge" in resp.data

    with app_module.app.app_context():
        user = User.query.filter_by(email="alex@example.com").first()
        assert user is not None
        assert user.check_password("password123")
        assert not user.is_premium
        assert not user.is_admin


def test_signup_rejects_invalid_email(client):
    resp = signup(client, email="not-an-email")
    assert resp.status_code == 200
    assert b"valid email" in resp.data


def test_signup_rejects_short_password(client):
    resp = signup(client, password="short")
    assert resp.status_code == 200
    assert b"at least 8 characters" in resp.data


def test_signup_rejects_duplicate_email(client):
    signup(client)
    client.get("/logout")
    resp = signup(client)
    assert resp.status_code == 200
    assert b"already exists" in resp.data


def test_login_with_correct_credentials(client):
    signup(client)
    client.get("/logout")

    resp = login(client)
    assert resp.status_code == 200
    assert b"Logged in" in resp.data


def test_login_with_wrong_password_fails(client):
    signup(client)
    client.get("/logout")

    resp = login(client, password="wrongpassword")
    assert resp.status_code == 200
    assert b"Invalid email or password" in resp.data


def test_logout_requires_login(client):
    resp = client.get("/logout", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Please log in" in resp.data


def test_membership_prompts_login_when_anonymous(client):
    resp = client.get("/membership")
    assert resp.status_code == 200
    assert b"Log in" in resp.data
    assert b"Subscribe with Stripe" not in resp.data


def test_checkout_session_requires_login(client):
    resp = client.post("/create-checkout-session", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Please log in" in resp.data


def test_upi_qr_requires_login(client):
    resp = client.get("/upi-qr.png")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_admin_page_forbidden_for_regular_user(client):
    signup(client)
    resp = client.get("/admin")
    assert resp.status_code == 403


def test_admin_page_forbidden_for_anonymous(client):
    resp = client.get("/admin", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Please log in" in resp.data


def test_admin_email_is_promoted_on_signup(client, monkeypatch):
    monkeypatch.setattr(app_module.config, "ADMIN_EMAILS", {"boss@example.com"})
    signup(client, email="boss@example.com")

    resp = client.get("/admin")
    assert resp.status_code == 200
    assert b"boss@example.com" in resp.data


def test_admin_can_toggle_premium_for_another_user(client, monkeypatch):
    monkeypatch.setattr(app_module.config, "ADMIN_EMAILS", {"boss@example.com"})
    signup(client, email="member@example.com")
    client.get("/logout")
    signup(client, email="boss@example.com")

    with app_module.app.app_context():
        member = User.query.filter_by(email="member@example.com").first()
        member_id = member.id
        assert not member.is_premium

    resp = client.post(f"/admin/users/{member_id}/toggle-premium", follow_redirects=True)
    assert resp.status_code == 200

    with app_module.app.app_context():
        member = db.session.get(User, member_id)
        assert member.is_premium
