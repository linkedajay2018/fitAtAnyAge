import atexit
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

os.environ.setdefault("ENABLE_TRACING", "false")

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_db_path}")


@atexit.register
def _cleanup_test_db():
    try:
        os.close(_db_fd)
        os.remove(_db_path)
    except OSError:
        pass


import pytest

from fitafter40 import app as app_module
from fitafter40.core.models import db as db_module


@pytest.fixture(autouse=True)
def _reset_db():
    with app_module.app.app_context():
        db_module.session.remove()
        db_module.drop_all()
        db_module.create_all()
    yield


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    app_module.app.config["WTF_CSRF_ENABLED"] = False
    # Flask-Limiter reads app.config["RATELIMIT_ENABLED"] only once, inside
    # its own init_app() at import time — setting app.config here has no
    # effect after the fact. Toggle the extension's `enabled` attribute
    # directly instead, so tests that hit /login, /signup, /chat etc. many
    # times in a row (across the whole session, since `app` is a
    # module-level singleton) don't get rate-limited by each other.
    app_module.limiter.enabled = False
    with app_module.app.test_client() as test_client:
        yield test_client
