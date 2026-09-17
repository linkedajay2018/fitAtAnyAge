import io
import json
import os
import random
import re
from datetime import date
from functools import wraps
from urllib.parse import quote, quote_plus

import qrcode
import stripe
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request, redirect, session, url_for, flash, send_file, abort
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_babel import Babel, gettext as _, get_locale, lazy_gettext as _l
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from flask_wtf import CSRFProtect
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from fitAtAnyAge.core import config
from fitAtAnyAge.services.chatbot import get_ai_reply, get_faq_reply
from fitAtAnyAge.core.content import (
    AGE_GROUPS,
    AGE_GUIDANCE,
    BACKGROUND_IMAGES,
    DIET_GUIDANCE,
    GENERAL_SAFETY_TIPS,
    MOTIVATIONAL_QUOTES,
    PROTEIN_SOURCES,
    SUPPLEMENT_NOTE,
    WORKOUT_PLANS,
)
from fitAtAnyAge.services.mail import mail, send_password_reset_email, send_verification_email
from fitAtAnyAge.core.models import ContactMessage, ExerciseLogEntry, User, WorkoutProgress, db
from fitAtAnyAge.services.sso import PROVIDER_META, fetch_sso_profile, get_configured_providers, oauth, register_providers
from fitAtAnyAge.utils.tokens import EMAIL_VERIFY_SALT, PASSWORD_RESET_SALT, generate_token, verify_token
from fitAtAnyAge.utils.tracing import configure_tracing
from fitAtAnyAge.utils.units import format_hydration_target, format_protein_target, format_weight, lb_to_kg

load_dotenv()

# Resolve paths to templates and static files from project root
_base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_template_dir = os.path.join(_base_dir, "templates")
_static_dir = os.path.join(_base_dir, "static")
_instance_dir = os.path.join(_base_dir, "instance")
_translations_dir = os.path.join(_base_dir, "translations")

app = Flask(__name__, template_folder=_template_dir, static_folder=_static_dir, instance_path=_instance_dir)
app.config["BABEL_TRANSLATION_DIRECTORIES"] = _translations_dir
app.secret_key = config.SECRET_KEY

os.makedirs(app.instance_path, exist_ok=True)
app.config["SQLALCHEMY_DATABASE_URI"] = config.DATABASE_URL or (
    f"sqlite:///{os.path.join(app.instance_path, 'fitAtAnyAge.db')}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)
with app.app_context():
    db.create_all()

csrf = CSRFProtect(app)

register_providers(app)

app.config["MAIL_SERVER"] = config.MAIL_SERVER
app.config["MAIL_PORT"] = config.MAIL_PORT
app.config["MAIL_USE_TLS"] = config.MAIL_USE_TLS
app.config["MAIL_USERNAME"] = config.MAIL_USERNAME
app.config["MAIL_PASSWORD"] = config.MAIL_PASSWORD
app.config["MAIL_DEFAULT_SENDER"] = config.MAIL_DEFAULT_SENDER
mail.init_app(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri=config.RATELIMIT_STORAGE_URI,
    default_limits=[],
)

# Security headers (CSP, HSTS, X-Frame-Options, etc). force_https/
# session_cookie_secure are tied to config.FORCE_HTTPS so local http://
# dev keeps working — flip FORCE_HTTPS on once actually deployed behind
# HTTPS. The app loads no external scripts/styles/fonts, so a same-origin
# CSP needs no third-party allowlisting.
Talisman(
    app,
    force_https=config.FORCE_HTTPS,
    strict_transport_security=config.FORCE_HTTPS,
    session_cookie_secure=config.FORCE_HTTPS,
    content_security_policy={
        "default-src": "'self'",
        "img-src": "'self' data:",
        "object-src": "'none'",
    },
)


def select_locale():
    cookie_locale = request.cookies.get("locale")
    if cookie_locale in config.LANGUAGES:
        return cookie_locale
    return request.accept_languages.best_match(list(config.LANGUAGES.keys())) or config.DEFAULT_LOCALE


def select_units():
    cookie_units = request.cookies.get("units")
    if cookie_units in config.UNIT_SYSTEMS:
        return cookie_units
    return config.DEFAULT_UNIT_SYSTEM


babel = Babel(app, locale_selector=select_locale)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message = _l("Please log in to continue.")
login_manager.login_message_category = "error"
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


if config.ENABLE_TRACING:
    configure_tracing(app, service_name=config.OTEL_SERVICE_NAME, otlp_endpoint=config.OTEL_EXPORTER_OTLP_ENDPOINT)

tracer = trace.get_tracer(config.OTEL_SERVICE_NAME)

stripe.api_key = config.STRIPE_SECRET_KEY


@app.context_processor
def inject_site_config():
    return {
        "site_name": config.SITE_NAME,
        "site_tagline": config.SITE_TAGLINE,
        "site_description": config.SITE_DESCRIPTION,
        "site_url": config.DOMAIN,
        "contact_email": config.CONTACT_EMAIL,
        "premium_price_label": config.PREMIUM_PRICE_LABEL,
        "copyright_year": config.COPYRIGHT_YEAR,
        "motivation_quote": random.choice(MOTIVATIONAL_QUOTES),
        "motivation_quotes": MOTIVATIONAL_QUOTES,
        "background_images": [
            url_for("static", filename=f"backgrounds/{name}") for name in BACKGROUND_IMAGES
        ],
        "sso_providers": [
            {"id": pid, "label": PROVIDER_META[pid]["label"]} for pid in get_configured_providers()
        ],
        "current_locale": str(get_locale()),
        "available_languages": config.LANGUAGES,
        "unit_system": select_units(),
        # Strings script.js needs for JS-generated text (BMI results, chat
        # fallbacks). Built here with Python-level gettext rather than
        # Jinja's `{{ _(...) }}` in base.html: Jinja's i18n extension always
        # applies %-formatting to the result (even with zero kwargs), which
        # raises KeyError on any msgid containing a %(name)s token meant for
        # script.js's own client-side substitution instead.
        "js_i18n_strings": {
            "bmi_invalid": _("Enter a valid height and weight."),
            "bmi_result": _("Your BMI is %(bmi)s (%(category)s)"),
            "bmi_result_with_bodyfat": _("Your BMI is %(bmi)s (%(category)s). Estimated body fat: %(bodyfat)s%."),
            "bmi_underweight": _("Underweight"),
            "bmi_healthy": _("Healthy range"),
            "bmi_overweight": _("Overweight"),
            "bmi_obese": _("Obese"),
            "hr_invalid": _("Enter a valid age."),
            "hr_result": _(
                "Estimated max heart rate: %(max)s bpm. Moderate zone: %(modLow)s–%(modHigh)s bpm. "
                "Vigorous zone: %(vigLow)s–%(vigHigh)s bpm."
            ),
            "tdee_invalid": _("Enter a valid height, weight, and age."),
            "tdee_result": _("Estimated maintenance calories: %(tdee)s kcal/day (basal: %(bmr)s kcal/day)."),
            "orm_invalid": _("Enter a valid weight and reps (1–15)."),
            "orm_result_metric": _("Estimated one-rep max: %(orm)s kg"),
            "orm_result_imperial": _("Estimated one-rep max: %(orm)s lb"),
            "orm_table_percent": _("Percent of 1RM"),
            "orm_table_weight_metric": _("Weight (kg)"),
            "orm_table_weight_imperial": _("Weight (lb)"),
            "whr_invalid": _("Enter a valid waist and hip measurement."),
            "whr_result": _("Waist-to-hip ratio: %(ratio)s"),
            "whr_result_with_risk": _("Waist-to-hip ratio: %(ratio)s (%(risk)s risk)"),
            "whr_risk_low": _("low"),
            "whr_risk_moderate": _("moderate"),
            "whr_risk_high": _("high"),
            "age_recommendation": _("In your %(age)s — %(headline)s. %(blurb)s"),
            "chat_error": _("Something went wrong — please try again."),
            "chat_fallback": _("Sorry, I couldn't process that."),
        },
    }


@app.route("/set-language/<lang_code>")
def set_language(lang_code):
    if lang_code not in config.LANGUAGES:
        abort(404)
    response = redirect(request.referrer or url_for("index"))
    response.set_cookie("locale", lang_code, max_age=60 * 60 * 24 * 365)
    return response


@app.route("/set-units/<system>")
def set_units(system):
    if system not in config.UNIT_SYSTEMS:
        abort(404)
    response = redirect(request.referrer or url_for("index"))
    response.set_cookie("units", system, max_age=60 * 60 * 24 * 365)
    return response


def build_upi_uri(reference=None):
    note = f"{config.SITE_NAME} Premium Membership"
    if reference:
        note += f" ref {reference}"
    params = {
        "pa": config.UPI_VPA,
        "pn": config.UPI_PAYEE_NAME,
        "am": config.UPI_AMOUNT,
        "cu": "INR",
        "tn": note,
    }
    query = "&".join(f"{key}={quote(str(value))}" for key, value in params.items())
    return f"upi://pay?{query}"


def _send_verification_email(user):
    token = generate_token(user.email, EMAIL_VERIFY_SALT)
    verify_url = url_for("verify_email", token=token, _external=True)
    send_verification_email(user.email, verify_url)


def youtube_search_url(exercise_label):
    """Link to a YouTube search for the exercise, not a specific curated
    video — avoids pointing to a single video that may be wrong, low
    quality, or later removed."""
    name = exercise_label.split("—")[0].strip()
    return f"https://www.youtube.com/results?search_query={quote_plus(name + ' exercise tutorial')}"


def exercises_for_age(plan, age_id):
    """The plan's base exercise list with that age's overrides applied
    (see content.py's WORKOUT_PLANS comment) — index positions never
    change, only which text fills a given index."""
    overrides = plan.get("exercise_overrides_by_age", {}).get(age_id, {})
    return [overrides.get(i, exercise) for i, exercise in enumerate(plan["exercises"])]


@app.route("/")
def index():
    return render_template("index.html", age_groups=AGE_GROUPS, age_guidance=AGE_GUIDANCE)


def _resolve_plan_for_display(plan):
    """Builds the plan's exercises (label + video link) and organizes them
    into `plan['schedule']`'s day-by-day groups, for the no-age-selected
    default render. Returns a fresh dict — never mutates WORKOUT_PLANS
    itself, since that's shared module-level content.py data reused
    across every request."""
    exercises = [
        {"label": exercise, "video_url": youtube_search_url(exercise)}
        for exercise in plan["exercises"]
    ]
    schedule = [
        {
            "day_number": day["day_number"],
            "focus": day["focus"],
            "exercises": [{"index": i, **exercises[i]} for i in day["exercise_indices"]],
        }
        for day in plan["schedule"]
    ]
    return {**plan, "exercises": exercises, "schedule": schedule}


@app.route("/workouts")
def workouts():
    plans = [_resolve_plan_for_display(plan) for plan in WORKOUT_PLANS]
    # Full age x level exercise matrix for script.js to swap in when a
    # visitor picks an age — the page renders the plain (no-age-selected)
    # `plans` above by default; this JSON blob is what makes the exercise
    # text/video links actually change per age instead of just the
    # "Recommended for you" badge.
    exercises_by_age = {
        plan["level_id"]: {
            age["id"]: [
                {"label": exercise, "video_url": youtube_search_url(exercise)}
                for exercise in exercises_for_age(plan, age["id"])
            ]
            for age in AGE_GROUPS
        }
        for plan in WORKOUT_PLANS
    }
    return render_template(
        "workouts.html",
        plans=plans,
        age_groups=AGE_GROUPS,
        age_guidance=AGE_GUIDANCE,
        exercises_by_age=exercises_by_age,
    )


@app.route("/api/workout-progress")
@login_required
def api_get_workout_progress():
    rows = WorkoutProgress.query.filter_by(user_id=current_user.id, completed=True).all()
    progress = {}
    for row in rows:
        progress.setdefault(row.level_id, {})[str(row.exercise_index)] = True
    return jsonify(progress)


@app.route("/api/workout-progress", methods=["POST"])
@login_required
def api_save_workout_progress():
    data = request.get_json(silent=True) or {}
    level_id = data.get("level_id")
    exercise_index = data.get("exercise_index")
    completed = bool(data.get("completed"))

    valid_level_ids = {plan["level_id"] for plan in WORKOUT_PLANS}
    if level_id not in valid_level_ids or not isinstance(exercise_index, int):
        abort(400)

    entry = WorkoutProgress.query.filter_by(
        user_id=current_user.id, level_id=level_id, exercise_index=exercise_index
    ).first()
    if entry:
        entry.completed = completed
    else:
        entry = WorkoutProgress(
            user_id=current_user.id, level_id=level_id, exercise_index=exercise_index, completed=completed
        )
        db.session.add(entry)
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/safety")
def safety():
    return render_template(
        "safety.html",
        general_tips=GENERAL_SAFETY_TIPS,
        age_groups=AGE_GROUPS,
        age_guidance=AGE_GUIDANCE,
    )


@app.route("/diet")
def diet():
    unit_system = select_units()
    diet_guidance = {
        age_id: {
            **info,
            "protein_target_display": format_protein_target(*info["protein_target_kg"], unit_system),
            "hydration_target_display": format_hydration_target(
                *info["hydration_target_l"], unit_system, note=info["hydration_note"]
            ),
        }
        for age_id, info in DIET_GUIDANCE.items()
    }
    return render_template(
        "diet.html",
        age_groups=AGE_GROUPS,
        diet_guidance=diet_guidance,
        protein_sources=PROTEIN_SOURCES,
        supplement_note=SUPPLEMENT_NOTE,
    )


@app.route("/chat", methods=["POST"])
@limiter.limit("20 per minute")
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()

    if not message:
        return jsonify({"reply": str(_("Ask me something about training, diet, or hydration!"))})

    with tracer.start_as_current_span("chatbot.reply") as span:
        span.set_attribute("chatbot.ai_configured", config.CHATBOT_AI_CONFIGURED)
        span.set_attribute("chatbot.message_length", len(message))
        if config.CHATBOT_AI_CONFIGURED:
            try:
                reply = get_ai_reply(message)
                span.set_attribute("chatbot.backend", "ai")
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.set_attribute("chatbot.backend", "faq-fallback")
                reply = get_faq_reply(message)
        else:
            span.set_attribute("chatbot.backend", "faq")
            reply = get_faq_reply(message)

    return jsonify({"reply": reply})


@app.route("/membership")
def membership():
    reference = current_user.id if current_user.is_authenticated else None
    return render_template(
        "membership.html",
        stripe_configured=config.STRIPE_CONFIGURED,
        upi_configured=config.UPI_CONFIGURED,
        upi_uri=build_upi_uri(reference) if config.UPI_CONFIGURED and reference else None,
        upi_vpa=config.UPI_VPA,
        upi_amount=config.UPI_AMOUNT,
    )


@app.route("/upi-qr.png")
@login_required
def upi_qr():
    if not config.UPI_CONFIGURED:
        abort(404)

    with tracer.start_as_current_span("upi.generate_qr") as span:
        span.set_attribute("upi.vpa", config.UPI_VPA)
        span.set_attribute("upi.amount", config.UPI_AMOUNT)
        span.set_attribute("upi.reference_user_id", current_user.id)
        img = qrcode.make(build_upi_uri(current_user.id))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
    return send_file(buf, mimetype="image/png")


@app.route("/create-checkout-session", methods=["POST"])
@login_required
def create_checkout_session():
    if not config.STRIPE_CONFIGURED:
        flash(_("Payments aren't configured yet. See .env.example for Stripe setup."), "error")
        return redirect(url_for("membership"))

    with tracer.start_as_current_span("stripe.create_checkout_session") as span:
        span.set_attribute("stripe.price_id", config.STRIPE_PRICE_ID)
        span.set_attribute("user.id", current_user.id)
        try:
            session = stripe.checkout.Session.create(
                mode="subscription",
                line_items=[{"price": config.STRIPE_PRICE_ID, "quantity": 1}],
                customer_email=current_user.email,
                client_reference_id=str(current_user.id),
                success_url=config.DOMAIN + url_for("payment_success") + "?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=config.DOMAIN + url_for("payment_cancel"),
            )
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            flash(_("Could not start checkout: %(error)s", error=str(e)), "error")
            return redirect(url_for("membership"))

        span.set_attribute("stripe.checkout_session_id", session.id)

    return redirect(session.url, code=303)


@app.route("/payment-success")
@login_required
def payment_success():
    session_id = request.args.get("session_id")
    if config.STRIPE_CONFIGURED and session_id:
        try:
            checkout_session = stripe.checkout.Session.retrieve(session_id)
            if checkout_session.status == "complete" and str(checkout_session.client_reference_id) == str(current_user.id):
                current_user.is_premium = True
                db.session.commit()
        except Exception:
            pass
    return render_template("success.html")


@app.route("/payment-cancel")
def payment_cancel():
    return render_template("cancel.html")


@app.route("/tools")
def tools():
    return render_template("tools.html")


@app.route("/signup", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not EMAIL_RE.match(email):
            flash(_("Enter a valid email address."), "error")
        elif len(password) < 8:
            flash(_("Password must be at least 8 characters."), "error")
        elif User.query.filter_by(email=email).first():
            flash(_("An account with that email already exists."), "error")
        else:
            user = User(email=email, is_admin=email in config.ADMIN_EMAILS)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            _send_verification_email(user)
            flash(_("Welcome to %(site_name)s!", site_name=config.SITE_NAME), "success")
            flash(_("We've sent a verification link to %(email)s.", email=user.email), "success")
            return redirect(request.args.get("next") or url_for("index"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            if email in config.ADMIN_EMAILS and not user.is_admin:
                user.is_admin = True
                db.session.commit()
            login_user(user)
            flash(_("Logged in."), "success")
            return redirect(request.args.get("next") or url_for("index"))

        flash(_("Invalid email or password."), "error")

    return render_template("login.html")


@app.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()
        if user:
            token = generate_token(user.email, PASSWORD_RESET_SALT)
            reset_url = url_for("reset_password", token=token, _external=True)
            send_password_reset_email(user.email, reset_url)
        # Same message whether or not the email exists — otherwise this
        # form could be used to check which emails have an account here.
        flash(_("If an account exists for that email, we've sent a password reset link."), "success")
        return redirect(url_for("login"))

    return render_template("forgot_password.html")


@app.route("/reset-password/<token>", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    email = verify_token(token, PASSWORD_RESET_SALT, config.RESET_TOKEN_MAX_AGE_SECONDS)
    if not email:
        flash(_("That password reset link is invalid or has expired. Request a new one."), "error")
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        if len(password) < 8:
            flash(_("Password must be at least 8 characters."), "error")
        else:
            user = User.query.filter_by(email=email).first()
            if not user:
                abort(404)
            user.set_password(password)
            db.session.commit()
            flash(_("Your password has been reset. Log in with your new password."), "success")
            return redirect(url_for("login"))

    return render_template("reset_password.html", token=token)


@app.route("/verify-email/<token>")
def verify_email(token):
    email = verify_token(token, EMAIL_VERIFY_SALT, config.VERIFY_TOKEN_MAX_AGE_SECONDS)
    if not email:
        flash(_("That verification link is invalid or has expired."), "error")
        return redirect(url_for("index"))

    user = User.query.filter_by(email=email).first()
    if not user:
        abort(404)

    user.email_verified = True
    db.session.commit()
    flash(_("Your email has been verified — thanks!"), "success")
    return redirect(url_for("index"))


@app.route("/resend-verification", methods=["POST"])
@login_required
@limiter.limit("5 per minute")
def resend_verification():
    if current_user.email_verified:
        flash(_("Your email is already verified."), "success")
    else:
        _send_verification_email(current_user)
        flash(_("We've sent a new verification link to %(email)s.", email=current_user.email), "success")
    return redirect(request.referrer or url_for("index"))


def _find_or_create_sso_user(email, provider):
    """Auto-link by email: a Google/Facebook sign-in with the same email
    as an existing password account logs into that same account (so
    membership/premium status carries over) rather than creating a
    duplicate. A brand new email creates a fresh, password-less account."""
    email = email.strip().lower()
    user = User.query.filter_by(email=email).first()

    if user is None:
        # SSO providers already verify the email themselves, so a
        # brand-new SSO account starts pre-verified — no email round-trip
        # needed, unlike a password signup.
        user = User(
            email=email,
            is_admin=email in config.ADMIN_EMAILS,
            oauth_provider=provider,
            email_verified=True,
        )
        db.session.add(user)
    else:
        if email in config.ADMIN_EMAILS and not user.is_admin:
            user.is_admin = True
        if not user.oauth_provider:
            user.oauth_provider = provider

    db.session.commit()
    return user


@app.route("/login/<provider>")
def sso_login(provider):
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if provider not in get_configured_providers():
        abort(404)

    session["sso_next"] = request.args.get("next") or ""
    client = oauth.create_client(provider)
    redirect_uri = url_for("sso_callback", provider=provider, _external=True)
    return client.authorize_redirect(redirect_uri)


@app.route("/login/<provider>/callback")
def sso_callback(provider):
    if provider not in get_configured_providers():
        abort(404)

    client = oauth.create_client(provider)

    with tracer.start_as_current_span("sso.callback") as span:
        span.set_attribute("sso.provider", provider)
        try:
            token = client.authorize_access_token()
            email, _name = fetch_sso_profile(provider, client, token)
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            flash(_("Something went wrong signing you in — please try again."), "error")
            return redirect(url_for("login"))

        if not email:
            span.set_attribute("sso.email_missing", True)
            flash(
                _(
                    "We couldn't get an email address from your %(provider)s account. "
                    "Make sure your account has a verified email, or use email/password instead.",
                    provider=PROVIDER_META[provider]["label"],
                ),
                "error",
            )
            return redirect(url_for("login"))

        user = _find_or_create_sso_user(email, provider)
        span.set_attribute("user.id", user.id)

    login_user(user)
    flash(_("Logged in with %(provider)s.", provider=PROVIDER_META[provider]["label"]), "success")
    next_url = session.pop("sso_next", "") or url_for("index")
    return redirect(next_url)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash(_("Logged out."), "success")
    return redirect(url_for("index"))


@app.route("/account")
@login_required
def account():
    completed_rows = WorkoutProgress.query.filter_by(user_id=current_user.id, completed=True).all()
    completed_by_level = {}
    for row in completed_rows:
        completed_by_level[row.level_id] = completed_by_level.get(row.level_id, 0) + 1
    plan_progress = [
        {
            "level": plan["level"],
            "icon": plan["icon"],
            "done": completed_by_level.get(plan["level_id"], 0),
            "total": len(plan["exercises"]),
        }
        for plan in WORKOUT_PLANS
    ]
    last_activity = max((row.updated_at for row in completed_rows), default=None)

    return render_template(
        "account.html",
        has_password=bool(current_user.password_hash),
        provider_label=PROVIDER_META.get(current_user.oauth_provider, {}).get("label"),
        plan_progress=plan_progress,
        workout_completed_count=len(completed_rows),
        workout_total_count=sum(len(plan["exercises"]) for plan in WORKOUT_PLANS),
        workout_last_activity=last_activity,
        history_count=ExerciseLogEntry.query.filter_by(user_id=current_user.id).count(),
    )


@app.route("/account/email", methods=["POST"])
@login_required
def account_change_email():
    new_email = request.form.get("email", "").strip().lower()
    current_password = request.form.get("current_password", "")

    if not EMAIL_RE.match(new_email):
        flash(_("Enter a valid email address."), "error")
    elif current_user.password_hash and not current_user.check_password(current_password):
        flash(_("Current password is incorrect."), "error")
    elif new_email != current_user.email and User.query.filter_by(email=new_email).first():
        flash(_("An account with that email already exists."), "error")
    elif new_email != current_user.email:
        current_user.email = new_email
        current_user.email_verified = False
        db.session.commit()
        _send_verification_email(current_user)
        flash(_("Email updated. We've sent a verification link to %(email)s.", email=new_email), "success")
    return redirect(url_for("account"))


@app.route("/account/password", methods=["POST"])
@login_required
def account_change_password():
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")

    if current_user.password_hash and not current_user.check_password(current_password):
        flash(_("Current password is incorrect."), "error")
    elif len(new_password) < 8:
        flash(_("Password must be at least 8 characters."), "error")
    else:
        current_user.set_password(new_password)
        db.session.commit()
        flash(_("Password updated."), "success")
    return redirect(url_for("account"))


@app.route("/account/disconnect-sso", methods=["POST"])
@login_required
def account_disconnect_sso():
    if not current_user.oauth_provider:
        abort(404)
    if not current_user.password_hash:
        flash(_("Set a password first so you can still log in after disconnecting."), "error")
    else:
        current_user.oauth_provider = None
        db.session.commit()
        flash(_("Disconnected."), "success")
    return redirect(url_for("account"))


@app.route("/account/delete", methods=["POST"])
@login_required
def account_delete():
    confirm_email = request.form.get("confirm_email", "").strip().lower()
    current_password = request.form.get("current_password", "")

    if confirm_email != current_user.email:
        flash(_("Type your email address exactly to confirm deletion."), "error")
        return redirect(url_for("account"))
    if current_user.password_hash and not current_user.check_password(current_password):
        flash(_("Current password is incorrect."), "error")
        return redirect(url_for("account"))

    user = current_user._get_current_object()
    logout_user()
    WorkoutProgress.query.filter_by(user_id=user.id).delete()
    ExerciseLogEntry.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    flash(_("Your account has been deleted."), "success")
    return redirect(url_for("index"))


@app.route("/account/export")
@login_required
def account_export():
    progress_rows = WorkoutProgress.query.filter_by(user_id=current_user.id, completed=True).all()
    history_rows = ExerciseLogEntry.query.filter_by(user_id=current_user.id).order_by(
        ExerciseLogEntry.performed_on
    ).all()
    data = {
        "id": current_user.id,
        "email": current_user.email,
        "email_verified": current_user.email_verified,
        "oauth_provider": current_user.oauth_provider,
        "is_premium": current_user.is_premium,
        "is_admin": current_user.is_admin,
        "created_at": current_user.created_at.isoformat(),
        "workout_progress": [
            {
                "level_id": row.level_id,
                "exercise_index": row.exercise_index,
                "updated_at": row.updated_at.isoformat(),
            }
            for row in progress_rows
        ],
        "exercise_history": [
            {
                "exercise_name": row.exercise_name,
                "sets": row.sets,
                "reps": row.reps,
                "weight_kg": row.weight_kg,
                "duration_minutes": row.duration_minutes,
                "notes": row.notes,
                "performed_on": row.performed_on.isoformat(),
            }
            for row in history_rows
        ],
    }
    buf = io.BytesIO(json.dumps(data, indent=2).encode("utf-8"))
    return send_file(
        buf,
        mimetype="application/json",
        as_attachment=True,
        download_name=f"{config.SITE_NAME.lower()}-account-data.json",
    )


@app.route("/history")
@login_required
def history():
    page = max(request.args.get("page", 1, type=int) or 1, 1)
    pagination = (
        ExerciseLogEntry.query.filter_by(user_id=current_user.id)
        .order_by(ExerciseLogEntry.performed_on.desc(), ExerciseLogEntry.id.desc())
        .paginate(page=page, per_page=20, error_out=False)
    )
    unit_system = select_units()
    entries = [
        {
            "id": entry.id,
            "exercise_name": entry.exercise_name,
            "sets": entry.sets,
            "reps": entry.reps,
            "weight_display": format_weight(entry.weight_kg, unit_system),
            "duration_minutes": entry.duration_minutes,
            "notes": entry.notes,
            "performed_on": entry.performed_on,
        }
        for entry in pagination.items
    ]
    # Free-text suggestions only (a <datalist>, not a closed <select>) —
    # a user's real workout doesn't have to match a plan exercise, this
    # just makes the common case faster to fill in.
    exercise_suggestions = sorted({str(exercise) for plan in WORKOUT_PLANS for exercise in plan["exercises"]})
    return render_template(
        "history.html",
        entries=entries,
        pagination=pagination,
        exercise_suggestions=exercise_suggestions,
        total_count=ExerciseLogEntry.query.filter_by(user_id=current_user.id).count(),
        today=date.today().isoformat(),
    )


def _parse_optional_int(raw):
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value >= 0 else None


def _parse_optional_float(raw):
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if value >= 0 else None


@app.route("/history/add", methods=["POST"])
@login_required
def history_add():
    exercise_name = request.form.get("exercise_name", "").strip()
    if not exercise_name:
        flash(_("Enter an exercise name."), "error")
        return redirect(url_for("history"))

    performed_on = date.today()
    performed_on_raw = request.form.get("performed_on", "").strip()
    if performed_on_raw:
        try:
            performed_on = date.fromisoformat(performed_on_raw)
        except ValueError:
            flash(_("Enter a valid date."), "error")
            return redirect(url_for("history"))

    weight_raw = _parse_optional_float(request.form.get("weight"))
    weight_kg = lb_to_kg(weight_raw) if weight_raw is not None and select_units() == "imperial" else weight_raw

    entry = ExerciseLogEntry(
        user_id=current_user.id,
        exercise_name=exercise_name[:255],
        sets=_parse_optional_int(request.form.get("sets")),
        reps=_parse_optional_int(request.form.get("reps")),
        weight_kg=weight_kg,
        duration_minutes=_parse_optional_int(request.form.get("duration_minutes")),
        notes=(request.form.get("notes", "").strip()[:500] or None),
        performed_on=performed_on,
    )
    db.session.add(entry)
    db.session.commit()
    flash(_("Logged %(exercise)s.", exercise=exercise_name), "success")
    return redirect(url_for("history"))


@app.route("/history/<int:entry_id>/delete", methods=["POST"])
@login_required
def history_delete(entry_id):
    entry = db.session.get(ExerciseLogEntry, entry_id)
    if not entry or entry.user_id != current_user.id:
        abort(404)
    db.session.delete(entry)
    db.session.commit()
    flash(_("Entry deleted."), "success")
    return redirect(url_for("history"))


@app.route("/admin")
@admin_required
def admin_users():
    query = request.args.get("q", "").strip()
    users_query = User.query
    if query:
        users_query = users_query.filter(User.email.ilike(f"%{query}%"))
    users = users_query.order_by(User.created_at.desc()).all()
    unread_message_count = ContactMessage.query.filter_by(is_read=False).count()
    return render_template(
        "admin.html", users=users, query=query, unread_message_count=unread_message_count
    )


@app.route("/admin/users/<int:user_id>/toggle-premium", methods=["POST"])
@admin_required
def admin_toggle_premium(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    user.is_premium = not user.is_premium
    db.session.commit()
    flash(_("Updated %(email)s's membership.", email=user.email), "success")
    return redirect(url_for("admin_users", q=request.form.get("q", "")))


@app.route("/admin/messages")
@admin_required
def admin_messages():
    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return render_template("admin_messages.html", messages=messages)


@app.route("/admin/messages/<int:message_id>/toggle-read", methods=["POST"])
@admin_required
def admin_toggle_message_read(message_id):
    message = db.session.get(ContactMessage, message_id)
    if not message:
        abort(404)
    message.is_read = not message.is_read
    db.session.commit()
    return redirect(url_for("admin_messages"))


@app.route("/admin/messages/<int:message_id>/delete", methods=["POST"])
@admin_required
def admin_delete_message(message_id):
    message = db.session.get(ContactMessage, message_id)
    if not message:
        abort(404)
    db.session.delete(message)
    db.session.commit()
    flash(_("Message deleted."), "success")
    return redirect(url_for("admin_messages"))


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        message = request.form.get("message", "").strip()
        if not name or not message:
            flash(_("Please fill in both your name and message."), "error")
        elif not EMAIL_RE.match(email):
            flash(_("Enter a valid email address."), "error")
        else:
            db.session.add(ContactMessage(name=name, email=email, message=message))
            db.session.commit()
            flash(_("Thanks %(name)s, we received your message!", name=name), "success")
            return redirect(url_for("contact"))
    return render_template("contact.html")


PUBLIC_PAGES = ["index", "workouts", "diet", "tools", "safety", "membership", "contact", "login", "signup"]


@app.route("/robots.txt")
def robots_txt():
    lines = [
        "User-agent: *",
        "Allow: /",
        f"Sitemap: {config.DOMAIN.rstrip('/')}{url_for('sitemap_xml')}",
    ]
    return Response("\n".join(lines), mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap_xml():
    urls = "".join(
        f"<url><loc>{config.DOMAIN.rstrip('/')}{url_for(page)}</loc></url>" for page in PUBLIC_PAGES
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>'
    )
    return Response(xml, mimetype="application/xml")


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(_error):
    return render_template("500.html"), 500


if __name__ == "__main__":
    if not config.STRIPE_CONFIGURED:
        print("[!] Stripe is NOT configured — set STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY, "
              "and STRIPE_PRICE_ID in .env (see .env.example). The Subscribe button won't appear until then.")
    if not config.UPI_CONFIGURED:
        print("[!] UPI is NOT configured — set UPI_VPA in .env (see .env.example). "
              "The QR code won't appear until then.")
    if not config.GOOGLE_CONFIGURED:
        print("[!] Google SSO is NOT configured — set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET "
              "in .env (see .env.example). The 'Continue with Google' button won't appear until then.")
    if not config.FACEBOOK_CONFIGURED:
        print("[!] Facebook SSO is NOT configured — set FACEBOOK_CLIENT_ID and FACEBOOK_CLIENT_SECRET "
              "in .env (see .env.example). The 'Continue with Facebook' button won't appear until then.")
    if not config.MAIL_CONFIGURED:
        print("[!] MAIL is NOT configured — set MAIL_SERVER, MAIL_USERNAME, and MAIL_PASSWORD "
              "in .env (see .env.example). Password reset/verification emails will print to the "
              "console instead of being sent.")
    app.run(debug=config.DEBUG, port=config.PORT)
