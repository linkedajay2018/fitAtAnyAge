from datetime import date, datetime, timezone

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    # Nullable: an account created via SSO only (Google/Facebook) has no
    # password until it sets one, either from Account Settings or via the
    # password-reset flow (an SSO-only account can use /reset-password to
    # set its first password — see app.py's reset_password()).
    password_hash = db.Column(db.String(255), nullable=True)
    # Which SSO provider this account first linked, if any ("google",
    # "facebook") — informational only, doesn't restrict login to that
    # provider. Accounts are matched/linked by email (see app.py).
    oauth_provider = db.Column(db.String(32), nullable=True)
    is_premium = db.Column(db.Boolean, nullable=False, default=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    # SSO accounts are marked verified immediately (the provider already
    # verified the email) — only password signups start unverified.
    email_verified = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)


class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class WorkoutProgress(db.Model):
    # One row per (user, plan, exercise). `exercise_index` is the
    # exercise's position within content.py's WORKOUT_PLANS[level_id]
    # ["exercises"] list — stable across locales, unlike the translated
    # exercise label text (see content.py's level/level_id comment for why
    # translated display text can't double as a matching/storage key).
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    level_id = db.Column(db.String(32), nullable=False)
    exercise_index = db.Column(db.Integer, nullable=False)
    completed = db.Column(db.Boolean, nullable=False, default=True)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (db.UniqueConstraint("user_id", "level_id", "exercise_index", name="uq_workout_progress_entry"),)


class ExerciseLogEntry(db.Model):
    # A free-form, manually-logged workout history entry — deliberately
    # not tied to WORKOUT_PLANS' exercises (see app.py's history()): a
    # user's real workout doesn't have to match a plan exercise exactly,
    # and letting `exercise_name` be plain text keeps that flexible.
    # `weight_kg` is always stored in metric regardless of the visitor's
    # unit_system preference at the time of entry — same "canonical
    # metric storage, convert at display time" pattern as content.py's
    # DIET_GUIDANCE (see units.py) — so a later unit-system switch doesn't
    # change the meaning of past entries.
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    exercise_name = db.Column(db.String(255), nullable=False)
    sets = db.Column(db.Integer, nullable=True)
    reps = db.Column(db.Integer, nullable=True)
    weight_kg = db.Column(db.Float, nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.String(500), nullable=True)
    performed_on = db.Column(db.Date, nullable=False, default=date.today)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
