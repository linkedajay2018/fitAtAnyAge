"""All environment-derived configuration in one place. Nothing else in the
app should call os.environ.get() directly — add new settings here instead,
with a sensible local-dev default."""

import os


def _bool_env(name, default="false"):
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes")


# --- Flask / security -------------------------------------------------
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
DATABASE_URL = os.environ.get("DATABASE_URL")  # None -> app.py builds instance/fitAtAnyAge.db
PORT = int(os.environ.get("PORT", "5050"))
DEBUG = _bool_env("FLASK_DEBUG", "true")

# --- Site branding / SEO -----------------------------------------------
SITE_NAME = os.environ.get("SITE_NAME", "FitAtAnyAge")
SITE_TAGLINE = os.environ.get("SITE_TAGLINE", "Strength and mobility training for every decade — 20s to 70s")
SITE_DESCRIPTION = os.environ.get(
    "SITE_DESCRIPTION",
    "Workout plans, safety tips, and tools tailored to your age, from your 20s through your 70s.",
)
# The site's public base URL. Also used to build Stripe's redirect URLs.
DOMAIN = os.environ.get("DOMAIN", f"http://127.0.0.1:{PORT}")
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "hello@example.com")
COPYRIGHT_YEAR = os.environ.get("COPYRIGHT_YEAR", "2026")

# Membership pricing shown in marketing copy. The amount actually billed is
# defined on Stripe's/UPI's side (STRIPE_PRICE_ID, UPI_AMOUNT below) — this
# is display text only, so keep it in sync with those if you change price.
PREMIUM_PRICE_LABEL = os.environ.get("PREMIUM_PRICE_LABEL", "$19.99 / month")

# --- Language / i18n -----------------------------------------------------
# Display name per supported locale code (used by the nav switcher and by
# Babel to know what's available). Add a new language here + a translation
# catalog under translations/<code>/LC_MESSAGES/ — nothing else needs to
# change, app.py's locale selector and the nav switcher both read this.
LANGUAGES = {
    "en": "English",
    "hi": "हिन्दी",
}
DEFAULT_LOCALE = "en"

# --- Units ----------------------------------------------------------------
# Which measurement system the BMI calculator and Diet Plan protein/
# hydration numbers are shown in. Cookie-based, same pattern as LANGUAGES
# above — set via /set-units/<system>, read back by select_units() in
# app.py. The option labels themselves are hardcoded + wrapped in `_()`
# directly in base.html (not here) so pybabel's static extraction can find
# them — see the i18n section of CLAUDE.md for why a variable msgid isn't
# extractable.
UNIT_SYSTEMS = ["metric", "imperial"]
DEFAULT_UNIT_SYSTEM = "metric"

# --- Auth ---------------------------------------------------------------
ADMIN_EMAILS = {e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()}

# --- Email (password reset / verification) ---------------------------------
# Standard SMTP settings — works with Gmail, Amazon SES, Mailgun's SMTP
# endpoint, etc. Without these set, outgoing emails are printed to the
# console instead of actually sent (see mail.py) — the reset/verification
# flows are fully usable in local dev with zero setup.
MAIL_SERVER = os.environ.get("MAIL_SERVER", "")
MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
MAIL_USE_TLS = _bool_env("MAIL_USE_TLS", "true")
MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "") or MAIL_USERNAME or "no-reply@example.com"
MAIL_CONFIGURED = bool(MAIL_SERVER and MAIL_USERNAME and MAIL_PASSWORD)

# Password reset / email verification links stay valid for this long.
RESET_TOKEN_MAX_AGE_SECONDS = int(os.environ.get("RESET_TOKEN_MAX_AGE_SECONDS", str(60 * 60)))
VERIFY_TOKEN_MAX_AGE_SECONDS = int(os.environ.get("VERIFY_TOKEN_MAX_AGE_SECONDS", str(60 * 60 * 24 * 3)))

# --- Rate limiting -----------------------------------------------------
# Flask-Limiter storage backend. "memory://" is per-process — fine for a
# single dev/gunicorn-worker deployment; point this at Redis
# (e.g. redis://localhost:6379) for a real multi-worker deployment so
# limits are shared across workers instead of each worker having its own.
RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")

# --- Security headers --------------------------------------------------
# Forces HTTPS + HSTS via flask-talisman. Keep false for local http:// dev;
# set true once actually deployed behind HTTPS (the Docker image doesn't
# assume this for you, since it doesn't know if a reverse proxy in front of
# it already terminates TLS).
FORCE_HTTPS = _bool_env("FORCE_HTTPS", "false")

# --- SSO / OAuth login -----------------------------------------------------
# Each provider is independently optional — the "Continue with X" button
# only appears once that provider's CLIENT_ID/CLIENT_SECRET are both set.
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_CONFIGURED = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)

FACEBOOK_CLIENT_ID = os.environ.get("FACEBOOK_CLIENT_ID", "")
FACEBOOK_CLIENT_SECRET = os.environ.get("FACEBOOK_CLIENT_SECRET", "")
FACEBOOK_CONFIGURED = bool(FACEBOOK_CLIENT_ID and FACEBOOK_CLIENT_SECRET)

# --- Stripe ---------------------------------------------------------------
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID", "")
STRIPE_CONFIGURED = bool(STRIPE_SECRET_KEY and STRIPE_PRICE_ID)

# --- UPI ---------------------------------------------------------------
UPI_VPA = os.environ.get("UPI_VPA", "")
UPI_PAYEE_NAME = os.environ.get("UPI_PAYEE_NAME", "FitAtAnyAge")
UPI_AMOUNT = os.environ.get("UPI_AMOUNT", "999")
UPI_CONFIGURED = bool(UPI_VPA)

# --- Tracing ---------------------------------------------------------------
ENABLE_TRACING = _bool_env("ENABLE_TRACING", "true")
OTEL_SERVICE_NAME = os.environ.get("OTEL_SERVICE_NAME", "fitAtAnyAge")
OTEL_EXPORTER_OTLP_ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")

# --- Chatbot -------------------------------------------------------------
# Without a key, the chat widget still works — it answers from the FAQ
# knowledge base in content.py (CHATBOT_FAQ). Set ANTHROPIC_API_KEY to
# upgrade it to real AI-generated answers grounded in this site's content.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")
CHATBOT_AI_CONFIGURED = bool(ANTHROPIC_API_KEY)
