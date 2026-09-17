"""Signed, time-limited tokens for password reset and email verification
links. No database column needed — the token itself carries the email and
an embedded timestamp, signed with SECRET_KEY so it can't be forged, and
expires on its own after max_age_seconds."""

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from fitAtAnyAge.core import config

PASSWORD_RESET_SALT = "password-reset"
EMAIL_VERIFY_SALT = "email-verify"


def _serializer():
    return URLSafeTimedSerializer(config.SECRET_KEY)


def generate_token(email, salt):
    return _serializer().dumps(email, salt=salt)


def verify_token(token, salt, max_age_seconds):
    """Returns the embedded email, or None if the token is invalid,
    tampered with, or older than max_age_seconds."""
    try:
        return _serializer().loads(token, salt=salt, max_age=max_age_seconds)
    except (BadSignature, SignatureExpired):
        return None
