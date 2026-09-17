from unittest.mock import patch

from fitAtAnyAge import app as app_module
from fitAtAnyAge.core.models import User, db

from helpers import login, signup


def test_forgot_password_page_loads(client):
    resp = client.get("/forgot-password")
    assert resp.status_code == 200
    assert b"Forgot" in resp.data


def test_forgot_password_sends_email_for_existing_account(client):
    with patch("fitAtAnyAge.app.send_verification_email"):
        signup(client, email="hasaccount@example.com")
    client.get("/logout")

    with patch("fitAtAnyAge.app.send_password_reset_email") as mock_send:
        resp = client.post("/forgot-password", data={"email": "hasaccount@example.com"}, follow_redirects=True)

    assert resp.status_code == 200
    mock_send.assert_called_once()
    sent_email, sent_url = mock_send.call_args[0]
    assert sent_email == "hasaccount@example.com"
    assert "/reset-password/" in sent_url


def test_forgot_password_same_message_for_unknown_email(client):
    with patch("fitAtAnyAge.app.send_password_reset_email") as mock_send:
        resp = client.post("/forgot-password", data={"email": "nobody@example.com"}, follow_redirects=True)

    assert resp.status_code == 200
    assert b"sent a password reset link" in resp.data
    mock_send.assert_not_called()


def test_reset_password_with_valid_token_updates_password(client):
    with patch("fitAtAnyAge.app.send_verification_email"):
        signup(client, email="reset@example.com", password="oldpassword1")
    client.get("/logout")

    with app_module.app.app_context():
        token = app_module.generate_token("reset@example.com", app_module.PASSWORD_RESET_SALT)

    resp = client.post(f"/reset-password/{token}", data={"password": "newpassword1"}, follow_redirects=True)
    assert resp.status_code == 200
    assert b"has been reset" in resp.data

    login_resp = login(client, email="reset@example.com", password="newpassword1")
    assert b"Logged in" in login_resp.data


def test_reset_password_enforces_minimum_length(client):
    with patch("fitAtAnyAge.app.send_verification_email"):
        signup(client, email="short@example.com")
    client.get("/logout")

    with app_module.app.app_context():
        token = app_module.generate_token("short@example.com", app_module.PASSWORD_RESET_SALT)

    resp = client.post(f"/reset-password/{token}", data={"password": "short"}, follow_redirects=True)
    assert b"at least 8 characters" in resp.data


def test_reset_password_with_invalid_token_redirects(client):
    resp = client.get("/reset-password/not-a-real-token", follow_redirects=True)
    assert resp.status_code == 200
    assert b"invalid or has expired" in resp.data


def test_reset_password_with_wrong_salt_token_is_rejected(client):
    token = app_module.generate_token("someone@example.com", app_module.EMAIL_VERIFY_SALT)
    resp = client.get(f"/reset-password/{token}", follow_redirects=True)
    assert b"invalid or has expired" in resp.data


def test_sso_only_account_can_set_a_password_via_reset(client):
    with app_module.app.app_context():
        user = app_module._find_or_create_sso_user("ssoreset@example.com", "google")
        assert user.password_hash is None
        token = app_module.generate_token(user.email, app_module.PASSWORD_RESET_SALT)

    resp = client.post(f"/reset-password/{token}", data={"password": "brandnewpass1"}, follow_redirects=True)
    assert resp.status_code == 200

    login_resp = login(client, email="ssoreset@example.com", password="brandnewpass1")
    assert b"Logged in" in login_resp.data
