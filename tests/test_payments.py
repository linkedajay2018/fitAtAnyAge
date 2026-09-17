from unittest.mock import MagicMock, patch

from fitAtAnyAge import app as app_module
from fitAtAnyAge.core import config

from helpers import signup


def test_membership_shows_not_configured_by_default(client, monkeypatch):
    monkeypatch.setattr(app_module.config, "STRIPE_CONFIGURED", False)
    monkeypatch.setattr(app_module.config, "UPI_CONFIGURED", False)
    signup(client)

    resp = client.get("/membership")

    assert resp.status_code == 200
    assert b"Card payments aren" in resp.data
    assert b"UPI isn" in resp.data


def test_membership_shows_subscribe_button_when_stripe_configured(client, monkeypatch):
    monkeypatch.setattr(app_module.config, "STRIPE_CONFIGURED", True)
    signup(client)

    resp = client.get("/membership")

    assert resp.status_code == 200
    assert b"Subscribe with Stripe" in resp.data


def test_membership_shows_qr_code_when_upi_configured(client, monkeypatch):
    monkeypatch.setattr(app_module.config, "UPI_CONFIGURED", True)
    monkeypatch.setattr(app_module.config, "UPI_VPA", "test@upi")
    signup(client)

    resp = client.get("/membership")

    assert resp.status_code == 200
    assert b"/upi-qr.png" in resp.data
    assert b"Open in UPI App" in resp.data


def test_membership_shows_premium_status_instead_of_buttons(client, monkeypatch):
    monkeypatch.setattr(app_module.config, "STRIPE_CONFIGURED", True)
    signup(client)
    with app_module.app.app_context():
        from fitAtAnyAge.core.models import User, db

        user = User.query.filter_by(email="alex@example.com").first()
        user.is_premium = True
        db.session.commit()

    resp = client.get("/membership")

    assert resp.status_code == 200
    assert b"You're a Premium member" in resp.data
    assert b"Subscribe with Stripe" not in resp.data


def test_checkout_session_redirects_with_error_when_not_configured(client, monkeypatch):
    monkeypatch.setattr(app_module.config, "STRIPE_CONFIGURED", False)
    signup(client)

    resp = client.post("/create-checkout-session", follow_redirects=True)

    assert resp.status_code == 200
    assert b"Payments aren" in resp.data


def test_checkout_session_redirects_to_stripe_when_configured(client, monkeypatch):
    monkeypatch.setattr(app_module.config, "STRIPE_CONFIGURED", True)
    monkeypatch.setattr(app_module.config, "STRIPE_PRICE_ID", "price_123")
    signup(client)
    fake_session = MagicMock(url="https://checkout.stripe.com/test-session")

    with patch("fitAtAnyAge.app.stripe.checkout.Session.create", return_value=fake_session) as mock_create:
        resp = client.post("/create-checkout-session")

    assert resp.status_code == 303
    assert resp.headers["Location"] == "https://checkout.stripe.com/test-session"
    mock_create.assert_called_once()
    assert mock_create.call_args.kwargs["customer_email"] == "alex@example.com"


def test_checkout_session_handles_stripe_error_gracefully(client, monkeypatch):
    monkeypatch.setattr(app_module.config, "STRIPE_CONFIGURED", True)
    monkeypatch.setattr(app_module.config, "STRIPE_PRICE_ID", "price_123")
    signup(client)

    with patch("fitAtAnyAge.app.stripe.checkout.Session.create", side_effect=Exception("boom")):
        resp = client.post("/create-checkout-session", follow_redirects=True)

    assert resp.status_code == 200
    assert b"Could not start checkout" in resp.data


def test_upi_qr_is_404_when_not_configured(client, monkeypatch):
    monkeypatch.setattr(app_module.config, "UPI_CONFIGURED", False)
    signup(client)

    resp = client.get("/upi-qr.png")

    assert resp.status_code == 404


def test_upi_qr_returns_png_when_configured(client, monkeypatch):
    monkeypatch.setattr(app_module.config, "UPI_CONFIGURED", True)
    monkeypatch.setattr(app_module.config, "UPI_VPA", "test@upi")
    signup(client)

    resp = client.get("/upi-qr.png")

    assert resp.status_code == 200
    assert resp.content_type == "image/png"


def test_build_upi_uri_format(monkeypatch):
    monkeypatch.setattr(app_module.config, "UPI_VPA", "test@upi")
    monkeypatch.setattr(app_module.config, "UPI_PAYEE_NAME", "FitAfter40")
    monkeypatch.setattr(app_module.config, "UPI_AMOUNT", "999")

    uri = app_module.build_upi_uri()

    assert uri.startswith("upi://pay?")
    assert "pa=test%40upi" in uri
    assert "am=999" in uri
