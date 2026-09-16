# CLAUDE.md

Guidance for Claude Code (or any future contributor) working in this repo.

## What this is

**FitAtAnyAge** (displayed brand name — the project folder and some internal identifiers, e.g.
`instance/fitafter40.db`, are still named `fitafter40` for historical reasons; cosmetic, not renamed —
see "Deliberately not implemented" below) — a Flask website with workout plans, tools, and a paid
membership tier, for people training at any age, 20s through 70s. Single Flask app, SQLite, no
frontend framework (server-rendered Jinja2 + a little vanilla JS).

The site used to be scoped to "40+" only; it broadened to all ages via an age-decade selector
(`content.py`'s `AGE_GROUPS`/`AGE_GUIDANCE`) rather than a rewrite — keep that pattern in mind if scope
broadens further (don't hardcode age-specific copy outside `content.py`).

## Architecture

- **`app.py`** — all routes: pages, auth (signup/login/logout/admin), password reset
  (`/forgot-password`, `/reset-password/<token>`), email verification (`/verify-email/<token>`,
  `/resend-verification`), account settings (`/account` + `/account/*` POST actions — change
  email/password, disconnect SSO, delete account, export data), exercise history (`/history`,
  `/history/add`, `/history/<id>/delete` — see "Exercise history" below), Stripe checkout, UPI QR, SEO
  routes, `/chat`, error handlers. Wires up Flask-Mail, Flask-Limiter, flask-talisman — see their own
  sections below.
- **`chatbot.py`** — `get_faq_reply()` (keyword-matches `content.py`'s `CHATBOT_FAQ`, always available,
  zero config) and `get_ai_reply()` (Claude API via the `anthropic` SDK, used only when
  `config.CHATBOT_AI_CONFIGURED` — `ANTHROPIC_API_KEY` set; model id from `config.ANTHROPIC_MODEL`,
  default `claude-sonnet-4-5`, env-overridable). `/chat` tries AI first when configured and falls back
  to FAQ on any exception — the widget must never hard-fail on a failed API call (see "Known gotchas"
  for a real bug this swallowed silently once).
- **`config.py`** — the *only* place that reads `os.environ`. Every setting has a local-dev default.
  New configurable value? Add it here, not inline in `app.py`.
- **`content.py`** — static site copy: `WORKOUT_PLANS` (3 levels, each with a base `exercises` list
  **and** an `exercise_overrides_by_age` dict swapping in age-appropriate variants — see "Age-specific
  workout content"; each exercise's "▶ Watch" link is a generated **YouTube search**, not a hand-picked
  video id — `youtube_search_url()` in `app.py` — deliberate, since there's no way to vet a curated
  video for every exercise and a fixed id risks linking to something wrong/deleted), `GENERAL_SAFETY_TIPS`,
  `AGE_GROUPS`/`AGE_GUIDANCE` (per-decade recommended plan level, headline, blurb, safety tips),
  `DIET_GUIDANCE` (per-decade protein/hydration targets — **raw metric tuples, not display strings**,
  see "Units" below), `PROTEIN_SOURCES` (Animal/Plant/Supplement food list, not age-gated) +
  `SUPPLEMENT_NOTE`, `CHATBOT_FAQ`, `MOTIVATIONAL_QUOTES`, `BACKGROUND_IMAGES`. Kept separate from
  routing so editing copy never touches `app.py`.
  - `AGE_GUIDANCE[x]["recommended_level"]` must be a valid `WORKOUT_PLANS` level —
    `tests/test_age_groups.py` enforces this.
  - **`PROTEIN_SOURCES` entries use the key `"foods"`, never `"items"`** — `"items"` collides with
    `dict.items()` under Jinja's dot notation (`group.items` resolves to the bound method, not the
    key) and breaks the template silently until a `TypeError` at render time; happened once already.
  - A `CHATBOT_FAQ` answer must actually state the topic word (e.g. "protein" in the protein answer) —
    tests assert the keyword appears in the reply; caught a real vagueness bug once.
- **`models.py`** — `User` (email, **nullable** password hash — an SSO-only account has none, see
  `sso.py`; `oauth_provider`, `is_premium`, `is_admin`, `email_verified`). `User.check_password()`
  guards against `password_hash is None`, returns `False` rather than raising. `ContactMessage`
  (persisted `/contact` submissions, managed at `/admin/messages`). `WorkoutProgress` (one row per
  user+level_id+exercise_index checked off — see "Workout progress sync"). `ExerciseLogEntry` (free-text
  workout log, distinct from `WorkoutProgress` — see "Exercise history"). Adding a *column* to an
  existing model still hits the no-migrations gotcha below; a whole new model (table) does not.
- **`sso.py`** — Google/Facebook OAuth via Authlib. `oauth` (shared `OAuth()` client registry — `app.py`
  imports this exact object, so patching `app.oauth.create_client` in tests affects the real thing),
  `register_providers(app)` (startup-only; registers a provider only if its config is present —
  `/login/<provider>` checks `get_configured_providers()` *before* `oauth.create_client`, never after),
  `fetch_sso_profile(provider, client, token)` (extend this to add a new provider). SSO accounts get
  `email_verified=True` in `_find_or_create_sso_user()` since the provider already verified the email.
- **`tokens.py`** — signed, time-limited tokens (`itsdangerous.URLSafeTimedSerializer`) for password
  reset / email verification, no DB column needed. `generate_token(email, salt)` /
  `verify_token(token, salt, max_age_seconds)` — always pass the matching salt (`PASSWORD_RESET_SALT`
  vs `EMAIL_VERIFY_SALT`); a token from one salt is rejected under the other, so a reset link can't
  double as a verify link.
- **`mail.py`** — outgoing email, same graceful-degradation pattern as Stripe/UPI: without
  `config.MAIL_CONFIGURED`, `_send()` prints to console instead of sending — reset/verification flows
  work with zero SMTP setup. `app.py` builds the URL (`url_for(..., _external=True)`) and passes it in;
  `mail.py` never touches routing.
- **`tracing.py`** — OpenTelemetry setup. Takes `service_name`/`otlp_endpoint` as explicit params (not
  env reads) so it stays testable; `app.py` passes them from `config.py` (`service_name` defaults to
  `"fitafter40"`, overridable via `OTEL_SERVICE_NAME`).
- **`templates/`** — Jinja2, all extending `base.html`. Site-wide values (`site_name`, `site_tagline`,
  `premium_price_label`, `contact_email`, etc.) are injected via the `inject_site_config` context
  processor in `app.py` — don't hardcode brand/price/domain in a template.
- **`static/`** — `style.css`, `script.js` (checklist + localStorage progress, BMI calculator, age
  selector — `initAgeSelector()`), `favicon.svg`, `backgrounds/` (5 Pexels photos, [free-commercial-use
  license](https://www.pexels.com/license/), no attribution required). **Don't bulk-replace these
  without hand-reviewing each candidate** — Pexels also hosts photos unsuitable for a general all-ages
  fitness site (one was downloaded and rejected for exactly this before the current squat photo was
  picked). Source: `bg-sprint.jpg`→[38137157](https://www.pexels.com/photo/38137157/),
  `bg-squat.jpg`→[39219652](https://www.pexels.com/photo/39219652/),
  `bg-boxing.jpg`→[7991631](https://www.pexels.com/photo/7991631/),
  `bg-jump.jpg`→[7688862](https://www.pexels.com/photo/7688862/),
  `bg-kettlebell.jpg`→[3888411](https://www.pexels.com/photo/3888411/).
- **`templates/_age_selector.html`** — shared partial (pill buttons), included on `index.html`,
  `workouts.html`, `safety.html`. Add it here, not copy-pasted, for a new page.
- **`tests/`** — pytest + Flask's test client. `conftest.py` builds a temp-file SQLite DB for the whole
  session and resets schema before every test; `helpers.py` has shared `signup()`/`login()`.

## Internationalization (i18n)

Flask-Babel. Currently English (default) and Hindi (`hi`).

- **Locale selection** (`select_locale()` in `app.py`): cookie `locale` (set by
  `/set-language/<lang_code>`) → `Accept-Language` header → `config.DEFAULT_LOCALE`. New language =
  one entry in `config.LANGUAGES` plus a catalog under `translations/<code>/LC_MESSAGES/`; nav dropdown
  and locale selector both read `config.LANGUAGES` already.
- **`gettext`/`_()` vs `lazy_gettext`/`_l()`.** Use `_()` inside a request (route handlers, flash
  messages). Use `_l()` for strings defined at *import time*, outside any request context — every
  string in `content.py` and `login_manager.login_message`. `_l()` returns a `LazyString` that resolves
  to the current locale only when rendered inside a request — get this backwards and the string
  freezes into whatever locale was active at import time (usually English), for every visitor.
- **Jinja's `{{ _('...') }}` alias always applies `%`-formatting, even with zero kwargs** — a literal
  `%(x)s` with no matching kwarg raises `KeyError` at render time. This is why `js_i18n_strings` in
  `app.py` (client-side `%(bmi)s`-style tokens for `script.js`) is built with Python-level
  `gettext()` instead — that only `%`-formats when kwargs are actually passed. A template `_()` call
  with a literal `%` needs matching kwargs or `%%` escaping.
- **`level`/`level_id` (and `category`/`category_id`).** Some `content.py` values are used both as
  *displayed text* and an *internal matching key* — translating the display text would silently break
  matching if they shared one field. `WORKOUT_PLANS[i]["level"]` (translatable) has a stable untranslated
  `"level_id"` sibling used in `data-*` attributes, JS badge matching, localStorage keys, and
  `AGE_GUIDANCE`. Same for `PROTEIN_SOURCES`' `category`/`category_id`. **New `content.py` field that's
  both shown and compared elsewhere? Give it a stable `_id` sibling from the start.**
- **`CHATBOT_FAQ` keywords carry both English and Hindi terms** in one `"keywords"` list — `get_faq_reply()`
  does plain substring matching, no translation of the incoming message. Add matching terms in every
  supported language for a new FAQ entry.
- **`LazyString` defines `__html__()`**, so Jinja autoescape renders it **unescaped** — standard
  Flask-Babel behavior, but tests comparing rendered HTML against `content.py` strings should compare
  `str(the_lazy_string)` directly, not a manually-escaped version.
- **`get_faq_reply()` explicitly `str()`s its return value** before `/chat` `jsonify()`s it — FAQ
  answers are `LazyString`s, resolved inside the request where the correct locale is active.
  `get_ai_reply()`'s system prompt also tells Claude which language to answer in when not English.
- **Extracting/updating translations:**
  ```bash
  pybabel extract -F babel.cfg -k lazy_gettext -k _l \
    --ignore-dirs="venv .git instance tests" -o messages.pot .
  pybabel init -i messages.pot -d translations -l <code>   # one-time, only for a brand-new language
  pybabel update -i messages.pot -d translations           # for existing languages, after that
  pybabel compile -d translations
  ```
  `-k lazy_gettext -k _l` is required — pybabel's default keyword list skips `lazy_gettext`, so without
  it every `content.py` string is silently missed. `pybabel update` fuzzy-matches new msgids by
  similarity, which can attach a **wrong** existing translation instead of leaving it blank (marked
  `fuzzy`) — happened once when ~30 new strings were added. Fuzzy entries are excluded from the
  compiled `.mo` by default, but always grep `.po` for `#, fuzzy` after an `update` and fix every match.

## Account, password reset & email verification

- **Password reset and email verification both use signed tokens (`tokens.py`), not a DB column.** A
  token encodes email + timestamp, signed with `SECRET_KEY`; `verify_token()` rejects it past
  `config.RESET_TOKEN_MAX_AGE_SECONDS` (1 hour) / `VERIFY_TOKEN_MAX_AGE_SECONDS` (3 days) — both
  env-overridable (not in `.env.example`, defaults suit almost every deployment). Resetting
  `SECRET_KEY` invalidates every outstanding link — expected, not a bug.
- **`/forgot-password` always shows the same message** regardless of whether the email has an account —
  revealing that would let the form enumerate registered emails.
- **An SSO-only account can use `/reset-password/<token>` to *set* its first password**, not just reset
  one — `password_hash` starts `None` for SSO signups, and `reset_password()` doesn't distinguish
  setting from resetting. Intentional: the only way an SSO-only user adds a password as a second login
  path (`tests/test_password_reset.py::test_sso_only_account_can_set_a_password_via_reset`).
- **`/account/disconnect-sso` refuses if the account has no `password_hash`** — would otherwise lock the
  user out permanently. Hidden in the template too, but re-checked server-side (hidden isn't enforced).
- **`/account/delete` requires typing the account's own email exactly**, plus current password if set —
  type-to-confirm on top of (not instead of) CSRF protection.
- **Changing email resets `email_verified` to `False`** and re-sends verification to the new address.

## Rate limiting & security headers

- **Flask-Limiter** throttles `/login`/`/signup` (10/min, POST only), `/chat` (20/min),
  `/forgot-password` (5/min), `/reset-password/<token>` (10/min), `/resend-verification` (5/min).
  Storage is `config.RATELIMIT_STORAGE_URI` (default `memory://`, per-process — point at Redis for a
  real multi-worker deployment, or separate workers won't share limit counters).
- **flask-talisman** sets CSP (same-origin-only `default-src 'self'`), HSTS, X-Frame-Options, etc. — any
  external script/font/widget needs an explicit allowlist entry in `content_security_policy` in
  `app.py`, or the browser silently blocks it (a CSP violation in the console, never a server error).
  `force_https`/`session_cookie_secure` are tied to `config.FORCE_HTTPS` (default `false`) — enabling
  Talisman's secure-cookie defaults without also setting `FORCE_HTTPS=true` over real HTTPS stops the
  session cookie from being sent at all over plain HTTP.
- **No inline event handler attributes (`onclick=`, `onchange=`, etc.) anywhere in `templates/`.** The
  CSP has no `'unsafe-inline'` in `script-src`, so browsers silently ignore inline handlers — no
  console or server error, the handler just never fires (bit the language `<select>`'s
  `onchange=` once, undetected until manually re-tested). **Fixed pattern**: a `data-*` hook + a real
  listener in `script.js`, wired from `DOMContentLoaded` like every other `init*()`. Never add a new
  inline handler.

## Units (metric/imperial)

- **`units.py`** is the only metric↔imperial conversion point — `DIET_GUIDANCE` stores only metric
  numbers, and `format_protein_target()`/`format_hydration_target()` derive the imperial display string
  at render time. `/diet` calls these once per age group; templates just print the result, never
  convert themselves. Same canonical-metric-storage pattern is reused by Exercise History's `weight_kg`
  (see below) — store metric, convert only at display.
- **The BMI calculator is handled differently on purpose**: it's client-side only (no round trip), so
  `initBmiCalculator()` uses the standard imperial formula directly (`703 × lb / in²`) rather than
  converting to metric first. Which fields render (cm/kg vs ft+in/lb) is decided server-side from the
  `unit_system` cookie; JS just detects which fields exist via `form.dataset.unitSystem`.
- **`PROTEIN_SOURCES`' per-100g table is deliberately left in grams for both unit systems** — that's how
  nutrition labels work even in the US. Don't add imperial conversion if extending this table.
- **Switching units is a cookie (`units`)**, same mechanism as `locale` but different placement —
  `select_units()`/`/set-units/<system>`, whitelisted by `config.UNIT_SYSTEMS`. Unlike the language
  switcher (in `base.html`'s nav), the unit switcher lives only on `tools.html` next to the BMI
  calculator — but the preference is site-wide, also affecting the Diet Plan's numbers, which isn't
  obvious from the Tools page alone. Its option labels are hardcoded + wrapped in `_()` directly in
  `tools.html`, not looped from a config dict like `LANGUAGES` — pybabel needs a literal string
  argument to `_()` to extract it.

## Tools page calculators

### BMI calculator: sex and body fat % (not sex-adjusted BMI)

- **BMI itself isn't calculated differently by sex, deliberately** — WHO/CDC/NIH all use one unisex
  formula and cutoff set. Rather than invent different thresholds (which would fabricate non-real
  guidance), the sex-aware metric added was estimated body fat percentage.
- **`estimateBodyFatPercent(bmi, age, sex)` in `script.js`** implements Deurenberg et al. (1991):
  `1.2×BMI + 0.23×age − 10.8×sexFactor − 5.4` (`sexFactor` 1 male / 0 female — the source of the
  sex difference, reflecting women carrying more essential body fat at the same BMI). An estimate, not
  a measurement — the disclaimer says so and flags it's less accurate for very muscular people.
- **Age/sex fields are optional and independent of unit-system fields.** Without both valid, the
  calculator falls back to BMI alone (`bmi_result` vs `bmi_result_with_bodyfat` in `js_i18n_strings`).
  "Prefer not to say" behaves like leaving sex blank.

### The other four calculators

All five cards live in one `.tools-grid`, each self-contained (own form/result element/`init*Calculator()`),
no shared state beyond the `unit_system` cookie.

- **Target Heart Rate Zones** — max HR via "220 − age"; Moderate/Vigorous = AHA's standard 50–70% /
  70–85% bands. Age only, no unit dependency.
- **Daily Calorie Needs** — Mifflin-St Jeor BMR × activity factor (1.2–1.9) for TDEE. **Unlike BMI, this
  one converts imperial inputs to metric in JS first** — there's no standard native-imperial Mifflin-St
  Jeor the way there is for BMI, so converting first is correct here, not an inconsistency. Sex
  optional; omitted uses the midpoint of the male/female constants rather than forcing a choice.
- **1-Rep Max Estimator** — Epley formula (`weight × (1 + reps/30)`), reps capped at 15 (formula
  accuracy degrades beyond that). Renders a table of suggested weights at 50–90% of estimated max via
  `innerHTML` — safe, since every value is a translated header or computed number, never user input.
- **Waist-to-Hip Ratio** — the one calculator where sex-specific *risk thresholds* are standard (WHO):
  male <0.90/0.90–0.99/≥1.0, female <0.80/0.80–0.84/≥0.85. Deliberate contrast with BMI: the rule was
  never "make things differ by sex," it was "match what's actually true per metric." Sex optional;
  without it, only the raw ratio shows.
- **A stray literal `%` in a translatable msgid breaks `pybabel compile`, not `extract`.** pybabel
  auto-flags any msgid containing `%` as `python-format`; a bare `%` then fails `msgfmt` validation only
  at compile time. Fixed by rewording (`"% of 1RM"` → `"Percent of 1RM"`) rather than escaping — reword
  around a literal `%` in a translatable string rather than assuming `%%` does what it does in an
  actually-`%`-formatted one.

## Age-specific workout content

- **Each `WORKOUT_PLANS` entry has a base `exercises` list (6 items) plus an optional
  `exercise_overrides_by_age` dict** — only exercises where age genuinely changes what's appropriate get
  an override, rather than authoring 18 mostly-duplicate lists. Keyed by `AGE_GROUPS` id →
  `{exercise_index: replacement_text}`; missing entries fall back to the base exercise. Mirrors how a
  real trainer adjusts specific higher-risk movements, not a rewrite from scratch. Currently: `beginner`
  varies at 60s/70s; `intermediate` at 50s/60s/70s; `active` at 20s/50s/60s/70s; 30s/40s use the base
  list everywhere.
- **`exercises_for_age(plan, age_id)`** in `app.py` merges base + overrides preserving index positions;
  `/workouts` calls it per (level, age) — 18 calls — to build the `exercises_by_age` JSON embedded in
  the page. The default pre-selection render uses the plain base list.
- **`initAgeSelector()` in `script.js` swaps exercise text/video links in-place, keyed by
  `[data-exercise-index]`** (not by rebuilding the list) — this keeps `WorkoutProgress` valid across an
  age switch, since index 0 always means "the plan's first exercise slot" regardless of which age's
  text currently fills it. It captures each `<li>`'s as-rendered defaults into `dataset` once at init,
  so clearing the age selection restores them without a separate "no age" data entry.

## Day-wise workout schedule

- **Each `WORKOUT_PLANS` entry has a `schedule` list** — one entry per training day, matching
  `days_per_week`, grouping the flat `exercises` list into a Day 1/Day 2/... split.
  `tests/test_workout_schedule.py` enforces day count, full exercise coverage with no duplicates, and
  sequential day numbers.
- **`schedule[i]["exercise_indices"]` refers to the same global 0-5 `exercises` index space, never a
  day-local one** — same principle as the age-override system: an exercise (and its overrides, and its
  `WorkoutProgress` row) is defined once regardless of display grouping. The day split itself doesn't
  vary by age; only the exercise text within a slot does.
- **`_resolve_plan_for_display(plan)`** in `app.py` turns `schedule`'s index numbers into template-ready
  data, attaching each exercise's original global `index` for `data-exercise-index`. **Always returns a
  fresh dict — never mutates `WORKOUT_PLANS` in place** (shared module-level data reused across
  requests; mutating it would leak between requests).
- No `script.js` changes were needed for day-grouping — the checkbox/progress and age-selector queries
  already searched the whole card recursively, so the extra `.schedule-day` wrapper div didn't break
  either (the payoff of index-based, not DOM-position-based, design).

## Workout progress sync

- **Checklist state lives in two places for a logged-in visitor: `localStorage` and `WorkoutProgress`
  rows (synced across devices).** `initWorkoutChecklists()` fetches `/api/workout-progress` when
  authenticated and merges server state into localStorage — server wins on conflict. Anonymous visitors
  only use `localStorage`.
  - `GET /api/workout-progress` → `{level_id: {exercise_index: true}}`, unchecked exercises simply absent.
  - `POST /api/workout-progress` (`{level_id, exercise_index, completed}`) upserts one row; a
    `completed: false` POST doesn't delete the row — leaves history for a possible future view.
- **Checkbox `value` is the exercise's index (`loop.index0`), not the translated label text — a real,
  silent bug before the fix.** Using the translated label meant checking a box in English then
  switching to Hindi produced a different value string, so checked state silently didn't carry over
  across a locale switch — same "translated text as matching key" trap as `WORKOUT_PLANS["level"]`
  before `level_id`. The index fix solves both that and gives server sync a locale-stable key.
- **The Account Settings progress summary is a live query, not cached** — fine at this scale; would need
  aggregation if exercises-per-plan or history length grows a lot.
- Deleting an account explicitly deletes `WorkoutProgress` rows first — SQLite doesn't enforce the FK by
  default (Flask-SQLAlchemy doesn't turn on `PRAGMA foreign_keys`), so skipping this orphans rows
  silently rather than erroring.

## Exercise history

A free-form workout log, separate from `WorkoutProgress` above — don't confuse the two.
`WorkoutProgress` tracks checking off a specific plan exercise slot; `ExerciseLogEntry` (`models.py`)
is a manually-entered diary row for whatever a user actually did, with no required link to a plan.

- **Fields**: `exercise_name` (free text, up to 255 chars — deliberately not tied to `WORKOUT_PLANS`,
  since a real workout doesn't have to match a plan exercise), optional
  `sets`/`reps`/`weight_kg`/`duration_minutes`/`notes`, required `performed_on` (defaults today).
- **`weight_kg` is always stored metric**, same canonical-storage pattern as `DIET_GUIDANCE` (see
  "Units" above) — `/history/add` converts an imperial-entered weight via `lb_to_kg()`; `format_weight()`
  converts back for display. Keeps a later unit-system switch from changing the meaning of past entries.
- **Routes**: `/history` (paginated 20/page, own entries only); `/history/add` (POST, silently drops a
  negative/unparseable numeric field rather than erroring — permissive by design for a free-text log);
  `/history/<id>/delete` (ownership check → `404` on mismatch, same not-403 pattern used everywhere).
- The exercise-name `<datalist>` autocomplete is sourced from `WORKOUT_PLANS` purely as a convenience —
  non-binding, any free text is accepted.
- Wired into `/account` (`history_count` summary), `/account/export` (included in the JSON dump), and
  `/account/delete` (entries deleted before the user, same reasoning as `WorkoutProgress`).
- Test file: `tests/test_history.py`.

## Admin tools

- **`/admin` takes `?q=`** and filters `User.email` case-insensitively — plain server-rendered search,
  no JS. The Premium toggle form round-trips `q` through a hidden field so it doesn't reset the filter.
- **Contact form submissions persist** (`ContactMessage`), managed at `/admin/messages` (mark
  read/unread, delete) — replaced the old flash-and-discard behavior; if you see docs/code claiming
  Contact doesn't persist, that's stale. Also collects/validates an email so there's a way to reply.
- The unread-message badge on `/admin` is a live `COUNT` query — fine at this scale.

### Full file tree

```
fitafter40/
  app.py            # Flask routes, auth/authz, Stripe checkout, UPI QR, SEO, chat
  chatbot.py        # Chat assistant: FAQ matching + optional Claude API backend
  config.py         # Single source of truth for all env-derived settings
  content.py        # Site content: plans, diet, safety tips, age guidance, FAQ, quotes
  models.py         # SQLAlchemy models: User, ContactMessage, WorkoutProgress, ExerciseLogEntry
  sso.py            # Google/Facebook OAuth login (Authlib)
  tracing.py        # OpenTelemetry setup (console or OTLP/Jaeger export)
  mail.py           # Outgoing email (password reset, email verification)
  tokens.py         # Signed, time-limited tokens for reset/verify links
  units.py          # Metric<->imperial conversion (Diet Plan, Exercise History)
  babel.cfg         # pybabel extraction config (scans *.py and templates/**.html)
  translations/     # Per-locale .po/.mo catalogs (translations/<code>/LC_MESSAGES/)
  instance/         # SQLite database lives here (created automatically, gitignored)
  requirements.txt      # App dependencies
  requirements-dev.txt  # App dependencies + pytest
  .env.example      # Template for every setting in config.py (copy to .env)
  Dockerfile        # Container build (gunicorn-served)
  docker-compose.yml     # docker compose up --build
  .dockerignore     # Keeps venv/.env/tests out of the image
  pytest.ini        # Points pytest at tests/
  tests/            # Automated tests (pytest + Flask test client)
  templates/        # HTML pages (Jinja2), incl. 404.html/500.html
  static/style.css  # Styling
  static/script.js  # Checklist, BMI calc, age selector, chat, background rotator
  static/favicon.svg     # Site favicon
  static/backgrounds/    # Licensed Pexels photos for the background rotator
```

## Commands

```bash
# Local dev
source venv/bin/activate
pip install -r requirements.txt
python app.py                    # http://127.0.0.1:5050 (port via config.PORT)

# Tests
pip install -r requirements-dev.txt
pytest                           # or: pytest -v

# Docker (gunicorn + Jaeger for tracing)
cp .env.example .env
docker compose up --build        # app: :5050, Jaeger UI: :16686
```

Run `pytest` before considering any change to `app.py`, `config.py`, `models.py`, or a template done —
the suite is fast (well under a second) and covers auth, payments (Stripe mocked), tracing, SEO routes.

## Conventions

- **Config lives in `config.py`, content lives in `content.py`** — see Architecture above for what
  belongs in each. Never inline a new env-configurable value or site copy in `app.py`.
- **CSRF is global** (Flask-WTF `CSRFProtect(app)`). Every `<form method="post">` needs the hidden
  `csrf_token` field or the submit 400s. Tests disable this via `WTF_CSRF_ENABLED = False`.
- **Stripe/UPI are optional and must degrade gracefully.** Routes check `config.STRIPE_CONFIGURED` /
  `UPI_CONFIGURED` first; the app must work fully (minus payment buttons) with neither set — the
  default state for a fresh clone. Don't assume either is configured.
- **Premium status is verified server-side.** `/payment-success` re-fetches the Stripe session and
  checks `status == "complete"` + `client_reference_id` — never trusts the redirect alone. UPI has no
  webhook, so it's confirmed manually by an admin.
- **Admin role** is granted by email match against `config.ADMIN_EMAILS`, applied at both signup and
  login (promoting someone = adding their email + them logging in again, no DB edit). SSO logins go
  through the same check, not a separate path.
- **SSO accounts link to existing password accounts by email — an explicit product decision, not a
  default.** `_find_or_create_sso_user()` looks up by email first and logs into that account if found
  (first provider used wins, never overwritten) rather than creating a second account. Tradeoff: anyone
  controlling a matching-email Google/Facebook account could log into the linked FitAtAnyAge account
  too — accepted here, worth reconsidering if this pattern is copied into something higher-stakes.
- **Every route a template needs must exist for `url_for()`.** `PUBLIC_PAGES` in `app.py` (used by
  `/sitemap.xml`) must stay in sync with which routes are actually public/indexable.
- **Age selector is progressive enhancement, not a gate.** All age-group content renders server-side and
  is fully visible with JS off; `initAgeSelector()` only highlights/expands based on a stored choice.
  Don't hide content behind the selector — hurts SEO and no-JS users.
- **Motivational banner is global** (`base.html`, via `inject_site_config`), shown on every page
  including 404/500 and `/admin` — intentional, don't special-case it out without checking first.
- **Reusable CSS conventions** (`style.css`): `.kicker` (eyebrow line), `.page-lead` (intro paragraph),
  `ul.check-list` (checkmark lists — must use this selector form), `.stat-strip`/`.stat` (big-number
  callouts), `.card-icon`/`.plan-icon` (card emoji, set via content.py's `"icon"` field, not in
  template). Reuse these rather than inventing one-off styles.
- **The whole site assumes a light effective background and dark text** — several page headers render
  directly on `<main>`, not inside a white card, so `.bg-overlay` washes the background rotator with a
  near-opaque light tint rather than a dark one. A dark-themed "hero image" look would require
  re-theming every page's text color, not just the overlay.

## Known gotchas — do not repeat these

- **Adding a *column* to an existing model doesn't update an existing local `instance/*.db` — adding a
  whole new *model* (table) does.** `db.create_all()` creates any missing table on startup, but does
  **not** add a missing column to a table that already exists: adding `email_verified` to `User` threw
  `OperationalError: no such column` on every pre-existing dev DB. No migrations tool here (see
  "Deliberately not implemented"), so local-dev fix is deleting `instance/*.db` and letting it recreate
  — safe, gitignored, disposable. Does **not** work for real user data; that needs an actual migration
  (manual `ALTER TABLE`, or finally adding Alembic past toy-project scale).
- **Dockerfile `COPY` line drift.** A new top-level module has repeatedly been added without updating
  the `Dockerfile`'s `COPY` line, which would crash the container on import. **Add it to `COPY` in the
  same change** — check `grep -E "^(import|from) " app.py` against `ls *.py` and the `COPY` line agree.
  Verify with `docker build` (or `python -c "import app"` from a clean checkout). Also applies to
  non-`.py` asset dirs — `translations/` was missed once, which would silently serve English to every
  visitor in the container (no crash — Flask-Babel falls back to the raw msgid — just wrong output).
- **A JS-toggled `[hidden]` element must not have its own `display:` rule without also styling `[hidden]`
  explicitly.** `.chat-panel`'s `display: flex` silently overrode the browser's default
  `[hidden] { display: none }` — the panel showed open on every load until `.chat-panel[hidden] {
  display: none; }` was added. Any element toggled via `hidden` *and* carrying its own `display`
  override needs this same explicit rule.
- **A `content.py` dict's shape change silently broke a consumer nobody re-checked.** When
  `DIET_GUIDANCE`'s protein/hydration values were refactored to raw metric tuples (see "Units"),
  `chatbot.py`'s `_build_system_prompt()` kept reading the old pre-refactor keys, which no longer
  existed. Every `get_ai_reply()` call raised `KeyError`, silently caught by `/chat`'s fallback-to-FAQ
  (there for legitimate API failures) — so the AI chatbot appeared fine while never actually running,
  for as long as `ANTHROPIC_API_KEY` was set. `tests/test_chatbot.py` didn't catch it since it mocks
  `get_ai_reply` rather than exercising the real prompt builder. Fixed by reading the current tuple
  fields. **Lesson: when a `content.py` value's shape changes, grep every consumer, not just the
  obvious code path (`/diet`, `units.py`)** — a module borrowing the same dict for unrelated purposes
  is easy to miss, and a broad `except Exception` nearby can mask the bug indefinitely.

## Testing notes

- `units.py`'s format helpers work fine called directly with no Flask request context pushed
  (`flask_babel.gettext()` degrades gracefully with no active app/translations) — no
  `app.app_context()` wrapper needed, unlike DB queries.
- **Mock the verification email** (`patch("app.send_verification_email")`) in any `signup()`-calling
  test that needs a predictable response body or wants to assert on the mock's call args; otherwise
  signup still works (prints to console) and most tests don't need the mock.
- **`exercise_index` posts to `/api/workout-progress` as a JSON integer, not a string** — the route
  validates `isinstance(exercise_index, int)` and 400s otherwise, mirroring `script.js`'s `Number(cb.value)`.
- **Rate limiting is disabled per-test via `app_module.limiter.enabled = False` directly**, not
  `app.config["RATELIMIT_ENABLED"]` — Flask-Limiter only reads that config key once, at `init_app()`
  during module import, so setting it later from a fixture has no effect. `tests/test_security.py`
  re-enables the limiter for its own two tests and restores it in a `finally` block, since limiter/app
  are shared module-level state across the whole test session.
- **Password reset/verification emails are mocked like Stripe**: `patch("app.send_password_reset_email")`
  / `patch("app.send_verification_email")` (patch via `app.`, since these names are imported into
  `app.py`'s namespace) — assert on `mock.call_args` for recipient/URL rather than intercepting the
  console fallback.
- A `User` created inside a `with app_module.app.app_context():` block becomes a **detached SQLAlchemy
  instance** once the block exits — reading `user.id` afterward raises `DetachedInstanceError`. Capture
  what you need as a plain local variable *inside* the block (see `tests/test_account.py`).
- **i18n tests** force locale via `client.set_cookie("locale", "hi")` (the test client doesn't send
  `Accept-Language`). Compare HTML against raw UTF-8 bytes as usual, but for anything through
  `jsonify()` (e.g. `/chat`) compare `resp.get_json()["reply"]` instead — Flask's JSON encoder escapes
  non-ASCII as `\uXXXX`, so raw response bytes never contain the literal characters.
- Stripe is always mocked (`stripe.checkout.Session.create`/`.retrieve`) — no real network/API key.
- `config`/`app` module attributes are monkeypatched directly in tests rather than setting env vars,
  since `config.py` reads env once at import time. New config value read via `config.X`? Patch
  `config.X`, not `app_module.X` — `app.py` reads through the module directly, no copies held.
- The AI chatbot backend is mocked the same way: `patch("app.get_ai_reply", return_value=...)` (or
  `side_effect=Exception(...)` for the fallback path) + `monkeypatch.setattr(config,
  "CHATBOT_AI_CONFIGURED", True)`. No real `ANTHROPIC_API_KEY` needed — it's `False` by default, so FAQ
  is what every other test exercises.
- **SSO is tested by mocking `app.oauth.create_client`, not just `config.GOOGLE_CONFIGURED`.**
  Monkeypatching the config flag alone makes the route's guard pass but doesn't register a real Authlib
  client (that only happens once, at startup) — `oauth.create_client` would return `None` and crash
  unless also patched. See `tests/test_sso.py` for the mock shape. `_find_or_create_sso_user()` itself
  is tested directly with no mocking, since it only touches the DB.

## Deliberately not implemented

DB migrations (Alembic), CI/CD, legal pages (privacy/terms), 2FA/MFA, session/device management, and
account lockout after repeated failed logins (rate limiting on `/login` covers brute-force *volume*,
not a distributed attacker). Scoped out as follow-up work, not oversights — check with the user before
adding scope back in any of these directions.

Password reset, email verification, rate limiting, and the account settings page **were** in this same
category until explicitly requested and built — see the sections above.

Also deliberate: when the site broadened from "40+" to all ages, only *displayed* branding
(`config.py`'s `SITE_NAME`/`SITE_TAGLINE`/etc.) changed — internal identifiers still saying
`fitafter40` (project folder, `instance/fitafter40.db`, the localStorage key prefix, `OTEL_SERVICE_NAME`
default) were left alone deliberately. Invisible to end users; renaming them is large-blast-radius,
low-value — don't do it without the user explicitly asking.
