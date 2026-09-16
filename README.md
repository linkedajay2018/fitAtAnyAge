# FitAtAnyAge

Flask website with workout plans, diet/hydration guidance, safety tips,
and a chat assistant for people training at any age (20s–70s). For
architecture, feature details, and design rationale, see [CLAUDE.md](CLAUDE.md).

## Requirements

- Python 3.9+
- pip
- Docker (optional, for containerized run)

## Setup

```bash
cd fitafter40
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env.example` documents every setting inline (Stripe, UPI, Google/
Facebook SSO, AI chatbot, tracing, etc.) — all optional, the app runs
fully with `.env` left blank.

Generate a real `SECRET_KEY` (recommended before any use beyond quick
local testing):

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Run

```bash
source venv/bin/activate
python app.py
```

Open **http://127.0.0.1:5050**. Stop with `Ctrl+C`, then `deactivate` to
leave the virtualenv.

> macOS: if port 5050 is also taken, set `PORT` in `.env`.

## Test

```bash
pip install -r requirements-dev.txt
pytest        # or: pytest -v
```

## Docker

```bash
docker compose up --build
```

Open http://127.0.0.1:5050 (app) and http://localhost:16686 (Jaeger
tracing UI). Stop with `Ctrl+C`, or `docker compose down` to remove
containers.

Plain Docker, without Compose:

```bash
docker build -t fitafter40 .
docker run --rm -p 5050:5050 --env-file .env -v "$(pwd)/instance:/app/instance" fitafter40
```

## Translations

English and Hindi ship compiled. After editing a `.po` file under
`translations/`, recompile:

```bash
pybabel compile -d translations
```

## Troubleshooting

Stripe / UPI / Google / Facebook button not showing? That integration
isn't configured — check the terminal on startup, it prints a `[!]`
warning naming exactly which env var is missing for each one. Fill in
the matching values in `.env` (see `.env.example` for where to get each).
