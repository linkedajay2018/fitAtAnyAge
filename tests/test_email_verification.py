from unittest.mock import patch

import app as app_module
from models import User

from helpers import login, signup


def test_signup_creates_unverified_user_and_sends_verification_email(client):
    with patch("app.send_verification_email") as mock_send:
        signup(client, email="new@example.com")

    with app_module.app.app_context():
        user = User.query.filter_by(email="new@example.com").first()
        assert user.email_verified is False

    mock_send.assert_called_once()
    sent_email, sent_url = mock_send.call_args[0]
    assert sent_email == "new@example.com"
    assert "/verify-email/" in sent_url


def test_sso_account_is_pre_verified():
    with app_module.app.app_context():
        user = app_module._find_or_create_sso_user("ssoverified@example.com", "google")
        assert user.email_verified is True


def test_unverified_banner_shown_after_signup(client):
    with patch("app.send_verification_email"):
        resp = signup(client, email="unverified@example.com")
    assert b"verify your email" in resp.data.lower()


def test_verified_user_sees_no_banner(client):
    with patch("app.send_verification_email"):
        signup(client, email="willverify@example.com")

    with app_module.app.app_context():
        user = User.query.filter_by(email="willverify@example.com").first()
        token = app_module.generate_token(user.email, app_module.EMAIL_VERIFY_SALT)

    resp = client.get(f"/verify-email/{token}", follow_redirects=True)
    assert b"verify your email" not in resp.data.lower()


def test_verify_email_with_valid_token_marks_verified(client):
    with patch("app.send_verification_email"):
        signup(client, email="verifyme@example.com")

    with app_module.app.app_context():
        user = User.query.filter_by(email="verifyme@example.com").first()
        assert user.email_verified is False
        token = app_module.generate_token(user.email, app_module.EMAIL_VERIFY_SALT)

    resp = client.get(f"/verify-email/{token}", follow_redirects=True)
    assert resp.status_code == 200
    assert b"verified" in resp.data.lower()

    with app_module.app.app_context():
        user = User.query.filter_by(email="verifyme@example.com").first()
        assert user.email_verified is True


def test_verify_email_with_invalid_token_shows_error(client):
    resp = client.get("/verify-email/not-a-real-token", follow_redirects=True)
    assert resp.status_code == 200
    assert b"invalid or has expired" in resp.data


def test_verify_email_with_wrong_salt_token_is_rejected(client):
    # A password-reset token must not double as an email-verify token.
    token = app_module.generate_token("someone@example.com", app_module.PASSWORD_RESET_SALT)
    resp = client.get(f"/verify-email/{token}", follow_redirects=True)
    assert b"invalid or has expired" in resp.data


def test_resend_verification_requires_login(client):
    resp = client.post("/resend-verification")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_resend_verification_sends_when_unverified(client):
    with patch("app.send_verification_email"):
        signup(client, email="resend@example.com")

    with patch("app.send_verification_email") as mock_send:
        resp = client.post("/resend-verification", follow_redirects=True)

    assert resp.status_code == 200
    mock_send.assert_called_once()


def test_resend_verification_noop_when_already_verified(client):
    with patch("app.send_verification_email"):
        signup(client, email="alreadyverified@example.com")

    with app_module.app.app_context():
        user = User.query.filter_by(email="alreadyverified@example.com").first()
        user.email_verified = True
        from models import db

        db.session.commit()

    with patch("app.send_verification_email") as mock_send:
        resp = client.post("/resend-verification", follow_redirects=True)

    assert resp.status_code == 200
    assert b"already verified" in resp.data.lower()
    mock_send.assert_not_called()
