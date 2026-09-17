import json
from unittest.mock import patch

from fitAtAnyAge import app as app_module
from fitAtAnyAge.core.models import User, db

from helpers import login, signup


def test_account_page_requires_login(client):
    resp = client.get("/account")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_account_page_loads_for_logged_in_user(client):
    with patch("fitAtAnyAge.app.send_verification_email"):
        signup(client, email="acct@example.com")
    resp = client.get("/account")
    assert resp.status_code == 200
    assert b"acct@example.com" in resp.data


def test_change_email_requires_correct_current_password(client):
    with patch("fitAtAnyAge.app.send_verification_email"):
        signup(client, email="wrongpw@example.com", password="password123")

    resp = client.post(
        "/account/email",
        data={"email": "newaddr@example.com", "current_password": "notmypassword"},
        follow_redirects=True,
    )
    assert b"Current password is incorrect" in resp.data

    with app_module.app.app_context():
        user = User.query.filter_by(email="wrongpw@example.com").first()
        assert user is not None


def test_change_email_updates_and_resets_verification(client):
    with patch("fitAtAnyAge.app.send_verification_email"):
        signup(client, email="oldaddr@example.com", password="password123")

    with app_module.app.app_context():
        user = User.query.filter_by(email="oldaddr@example.com").first()
        user.email_verified = True
        db.session.commit()

    with patch("fitAtAnyAge.app.send_verification_email") as mock_send:
        resp = client.post(
            "/account/email",
            data={"email": "newaddr@example.com", "current_password": "password123"},
            follow_redirects=True,
        )

    assert resp.status_code == 200
    assert b"Email updated" in resp.data
    mock_send.assert_called_once()

    with app_module.app.app_context():
        old = User.query.filter_by(email="oldaddr@example.com").first()
        new = User.query.filter_by(email="newaddr@example.com").first()
        assert old is None
        assert new is not None
        assert new.email_verified is False


def test_change_email_rejects_duplicate(client):
    with patch("fitAtAnyAge.app.send_verification_email"):
        signup(client, email="taken@example.com")
        client.get("/logout")
        signup(client, email="mine@example.com", password="password123")

    resp = client.post(
        "/account/email",
        data={"email": "taken@example.com", "current_password": "password123"},
        follow_redirects=True,
    )
    assert b"already exists" in resp.data


def test_change_password_requires_correct_current_password(client):
    with patch("fitAtAnyAge.app.send_verification_email"):
        signup(client, email="pwchange@example.com", password="password123")

    resp = client.post(
        "/account/password",
        data={"current_password": "wrong", "new_password": "newpassword1"},
        follow_redirects=True,
    )
    assert b"Current password is incorrect" in resp.data


def test_change_password_updates_successfully(client):
    with patch("fitAtAnyAge.app.send_verification_email"):
        signup(client, email="pwok@example.com", password="password123")

    resp = client.post(
        "/account/password",
        data={"current_password": "password123", "new_password": "brandnewpass1"},
        follow_redirects=True,
    )
    assert b"Password updated" in resp.data
    client.get("/logout")

    login_resp = login(client, email="pwok@example.com", password="brandnewpass1")
    assert b"Logged in" in login_resp.data


def test_sso_only_account_can_set_initial_password(client):
    with app_module.app.app_context():
        user = app_module._find_or_create_sso_user("ssosetpw@example.com", "google")
        assert user.password_hash is None
        user_id = user.id

    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True

    resp = client.post(
        "/account/password",
        data={"new_password": "firstpassword1"},
        follow_redirects=True,
    )
    assert b"Password updated" in resp.data

    with app_module.app.app_context():
        refreshed = db.session.get(User, user_id)
        assert refreshed.password_hash is not None


def test_disconnect_sso_blocked_without_password(client):
    with app_module.app.app_context():
        user = app_module._find_or_create_sso_user("nopassword@example.com", "google")
        user_id = user.id

    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True

    resp = client.post("/account/disconnect-sso", follow_redirects=True)
    assert b"Set a password first" in resp.data

    with app_module.app.app_context():
        refreshed = db.session.get(User, user_id)
        assert refreshed.oauth_provider == "google"


def test_disconnect_sso_succeeds_with_password(client):
    with app_module.app.app_context():
        user = app_module._find_or_create_sso_user("hasboth@example.com", "google")
        user.set_password("password123")
        db.session.commit()
        user_id = user.id

    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True

    resp = client.post("/account/disconnect-sso", follow_redirects=True)
    assert b"Disconnected" in resp.data

    with app_module.app.app_context():
        refreshed = db.session.get(User, user_id)
        assert refreshed.oauth_provider is None


def test_delete_account_requires_exact_email_match(client):
    with patch("fitAtAnyAge.app.send_verification_email"):
        signup(client, email="deleteme@example.com", password="password123")

    resp = client.post(
        "/account/delete",
        data={"confirm_email": "wrong@example.com", "current_password": "password123"},
        follow_redirects=True,
    )
    assert b"Type your email address exactly" in resp.data

    with app_module.app.app_context():
        assert User.query.filter_by(email="deleteme@example.com").first() is not None


def test_delete_account_requires_correct_password(client):
    with patch("fitAtAnyAge.app.send_verification_email"):
        signup(client, email="deletewrongpw@example.com", password="password123")

    resp = client.post(
        "/account/delete",
        data={"confirm_email": "deletewrongpw@example.com", "current_password": "wrong"},
        follow_redirects=True,
    )
    assert b"Current password is incorrect" in resp.data


def test_delete_account_succeeds_and_logs_out(client):
    with patch("fitAtAnyAge.app.send_verification_email"):
        signup(client, email="deletesucceeds@example.com", password="password123")

    resp = client.post(
        "/account/delete",
        data={"confirm_email": "deletesucceeds@example.com", "current_password": "password123"},
        follow_redirects=True,
    )
    assert b"account has been deleted" in resp.data

    with app_module.app.app_context():
        assert User.query.filter_by(email="deletesucceeds@example.com").first() is None

    # session is logged out — /account now redirects to login
    account_resp = client.get("/account")
    assert account_resp.status_code == 302


def test_export_data_requires_login(client):
    resp = client.get("/account/export")
    assert resp.status_code == 302


def test_export_data_returns_expected_fields(client):
    with patch("fitAtAnyAge.app.send_verification_email"):
        signup(client, email="exportme@example.com")

    resp = client.get("/account/export")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["email"] == "exportme@example.com"
    assert data["email_verified"] is False
    assert "created_at" in data
    assert data["is_premium"] is False
