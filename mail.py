"""Outgoing email for password reset and email verification.

Same graceful-degradation pattern as Stripe/UPI: without MAIL_SERVER/
MAIL_USERNAME/MAIL_PASSWORD set (config.MAIL_CONFIGURED), emails are
printed to the console instead of actually sent — the reset/verification
flows are fully usable and testable with zero SMTP setup."""

from flask_mail import Mail, Message

import config

mail = Mail()


def _send(subject, recipient, body):
    if config.MAIL_CONFIGURED:
        msg = Message(subject=subject, recipients=[recipient], body=body, sender=config.MAIL_DEFAULT_SENDER)
        mail.send(msg)
    else:
        print(
            f"[!] MAIL is NOT configured — printing email instead of sending.\n"
            f"    To: {recipient}\n    Subject: {subject}\n    ---\n{body}\n    ---"
        )


def send_password_reset_email(email, reset_url):
    _send(
        subject=f"Reset your {config.SITE_NAME} password",
        recipient=email,
        body=(
            f"Someone (hopefully you) requested a password reset for your {config.SITE_NAME} account.\n\n"
            f"Reset your password here (link expires in {config.RESET_TOKEN_MAX_AGE_SECONDS // 60} minutes):\n"
            f"{reset_url}\n\n"
            "If you didn't request this, you can safely ignore this email."
        ),
    )


def send_verification_email(email, verify_url):
    _send(
        subject=f"Verify your {config.SITE_NAME} email address",
        recipient=email,
        body=(
            f"Welcome to {config.SITE_NAME}! Please verify your email address by clicking the link below "
            f"(link expires in {config.VERIFY_TOKEN_MAX_AGE_SECONDS // 3600} hours):\n\n"
            f"{verify_url}\n\n"
            "If you didn't create this account, you can safely ignore this email."
        ),
    )
