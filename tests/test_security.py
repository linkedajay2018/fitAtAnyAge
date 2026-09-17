from fitAtAnyAge import app as app_module


def test_security_headers_present(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Content-Security-Policy" in resp.headers
    assert resp.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert resp.headers["X-Content-Type-Options"] == "nosniff"


def test_csp_is_same_origin_only(client):
    resp = client.get("/")
    csp = resp.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp


def test_https_not_forced_in_local_dev(client):
    # config.FORCE_HTTPS defaults to false, so a plain http:// request must
    # not be redirected — otherwise local dev (and the test client itself,
    # which talks http) would break.
    resp = client.get("/")
    assert resp.status_code == 200


def test_login_is_rate_limited(client):
    # The shared `client` fixture disables the limiter for test isolation;
    # re-enable it here just for this test, then restore it so later tests
    # aren't affected by requests made in this one.
    app_module.limiter.enabled = True
    try:
        last_status = None
        for _ in range(20):
            resp = client.post("/login", data={"email": "nobody@example.com", "password": "wrong"})
            last_status = resp.status_code
            if last_status == 429:
                break
        assert last_status == 429
    finally:
        app_module.limiter.enabled = False


def test_chat_is_rate_limited(client):
    app_module.limiter.enabled = True
    try:
        last_status = None
        for _ in range(30):
            resp = client.post("/chat", json={"message": "hello"})
            last_status = resp.status_code
            if last_status == 429:
                break
        assert last_status == 429
    finally:
        app_module.limiter.enabled = False
