FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY templates/ templates/
COPY static/ static/
COPY translations/ translations/

EXPOSE 5050

# Shell form so $PORT (set via -e/--env-file, e.g. by a hosting platform)
# is substituted at container start; falls back to 5050.
ENV PYTHONPATH=/app/src
CMD gunicorn --bind 0.0.0.0:${PORT:-5050} fitAtAnyAge.app:app
