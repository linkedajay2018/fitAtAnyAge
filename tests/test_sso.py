from unittest.mock import MagicMock, patch

from fitafter40 import app as app_module
from fitafter40.core import config
from fitafter40.core.models import User, db

from helpers import signup


def test_find_or_create_sso_user_creates_new_account():
    with app_module.app.app_context():
        user = app_module._find_or_create_sso_user("newperson@example.com", "google")

        assert user.email == "newperson@example.com"
        assert user.oauth_provider == "google"
        assert user.password_hash is None
        assert not user.is_admin


def test_find_or_create_sso_user_links_existing_password_account_by_email(client):
    signup(client, email="shared@example.com", password="password123")

    with app_module.app.app_context():
        before = User.query.filter_by(email="shared@example.com").first()
        assert before.password_hash is not None
        assert before.oauth_provider is None

        user = app_module._find_or_create_sso_user("shared@example.com", "facebook")

        assert user.id == before.id
        assert user.password_hash is not None  # untouched, still has a password
        assert user.oauth_provider == "facebook"


def test_find_or_create_sso_user_does_not_overwrite_existing_oauth_provider():
    with app_module.app.app_context():
        user = app_module._find_or_create_sso_user("both@example.com", "google")
        db.session.refresh(user)

        user_again = app_module._find_or_create_sso_user("both@example.com", "facebook")

        assert user_again.id == user.id
        assert user_again.oauth_provider == "google"  # first provider wins, not overwritten


def test_find_or_create_sso_user_promotes_admin(monkeypatch):
    monkeypatch.setattr(app_module.config, "ADMIN_EMAILS", {"boss@example.com"})
    with app_module.app.app_context():
        user = app_module._find_or_create_sso_user("boss@example.com", "google")
        assert user.is_admin


def test_check_password_on_sso_only_account_is_safe():
    with app_module.app.app_context():
        user = app_module._find_or_create_sso_user("nopassword@example.com", "google")
        assert user.check_password("anything") is False


def test_sso_login_404s_for_unconfigured_provider(client):
    resp = client.get("/login/google")
    assert resp.status_code == 404


def test_sso_login_404s_for_unknown_provider(client, monkeypatch):
    monkeypatch.setattr(app_module.config, "GOOGLE_CONFIGURED", True)
    resp = client.get("/login/not-a-real-provider")
    assert resp.status_code == 404


def test_sso_callback_404s_for_unconfigured_provider(client):
    resp = client.get("/login/google/callback")
    assert resp.status_code == 404


def test_login_page_hides_sso_buttons_when_not_configured(client):
    resp = client.get("/login")
    assert resp.status_code == 200
    assert b"Continue with Google" not in resp.data
    assert b"Continue with Facebook" not in resp.data


def test_login_page_shows_sso_buttons_when_configured(client, monkeypatch):
    monkeypatch.setattr(app_module.config, "GOOGLE_CONFIGURED", True)
    monkeypatch.setattr(app_module.config, "FACEBOOK_CONFIGURED", True)
    resp = client.get("/login")
    assert resp.status_code == 200
    assert b"Continue with Google" in resp.data
    assert b"Continue with Facebook" in resp.data


def test_sso_login_redirects_to_provider_when_configured(client, monkeypatch):
    monkeypatch.setattr(app_module.config, "GOOGLE_CONFIGURED", True)
    mock_client = MagicMock()
    mock_client.authorize_redirect.return_value = app_module.redirect("https://accounts.google.com/fake-consent-screen")

    with patch("fitafter40.app.oauth.create_client", return_value=mock_client):
        resp = client.get("/login/google")

    assert resp.status_code == 302
    assert "accounts.google.com" in resp.headers["Location"]
    mock_client.authorize_redirect.assert_called_once()


def test_sso_callback_creates_and_logs_in_new_user(client, monkeypatch):
    monkeypatch.setattr(app_module.config, "GOOGLE_CONFIGURED", True)
    mock_client = MagicMock()
    mock_client.authorize_access_token.return_value = {
        "userinfo": {"email": "fresh.from.google@example.com", "name": "Fresh Google User"}
    }

    with patch("fitafter40.app.oauth.create_client", return_value=mock_client):
        resp = client.get("/login/google/callback", follow_redirects=True)

    assert resp.status_code == 200
    assert b"Logged in with Google" in resp.data

    with app_module.app.app_context():
        user = User.query.filter_by(email="fresh.from.google@example.com").first()
        assert user is not None
        assert user.oauth_provider == "google"


def test_sso_callback_handles_missing_email_gracefully(client, monkeypatch):
    monkeypatch.setattr(app_module.config, "FACEBOOK_CONFIGURED", True)
    mock_client = MagicMock()
    mock_client.authorize_access_token.return_value = {"access_token": "fake"}
    mock_client.get.return_value.json.return_value = {"id": "123", "name": "No Email Person"}

    with patch("fitafter40.app.oauth.create_client", return_value=mock_client):
        resp = client.get("/login/facebook/callback", follow_redirects=True)

    assert resp.status_code == 200
    assert b"couldn" in resp.data.lower()


def test_sso_callback_falls_back_gracefully_on_provider_error(client, monkeypatch):
    monkeypatch.setattr(app_module.config, "GOOGLE_CONFIGURED", True)
    mock_client = MagicMock()
    mock_client.authorize_access_token.side_effect = Exception("provider rejected the request")

    with patch("fitafter40.app.oauth.create_client", return_value=mock_client):
        resp = client.get("/login/google/callback", follow_redirects=True)

    assert resp.status_code == 200
    assert b"went wrong" in resp.data.lower()
