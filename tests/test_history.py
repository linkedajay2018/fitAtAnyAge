from unittest.mock import patch

from fitafter40 import app as app_module
from fitafter40.core.models import ExerciseLogEntry, db

from helpers import signup


def _signup(client, email="alex@example.com"):
    with patch("fitafter40.app.send_verification_email"):
        return signup(client, email=email)


def test_history_page_requires_login(client):
    resp = client.get("/history")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_history_add_requires_login(client):
    resp = client.post("/history/add", data={"exercise_name": "Squats"})
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_history_page_loads_empty_for_new_user(client):
    _signup(client)
    resp = client.get("/history")
    assert resp.status_code == 200
    assert b"Nothing logged yet" in resp.data


def test_history_add_creates_entry(client):
    _signup(client, email="logger@example.com")
    resp = client.post(
        "/history/add",
        data={
            "exercise_name": "Goblet squats",
            "sets": "3",
            "reps": "10",
            "weight": "20",
            "duration_minutes": "",
            "notes": "Felt good",
            "performed_on": "2026-01-15",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Logged Goblet squats" in resp.data
    assert b"Goblet squats" in resp.data

    with app_module.app.app_context():
        entry = ExerciseLogEntry.query.filter_by(exercise_name="Goblet squats").first()
        assert entry is not None
        assert entry.sets == 3
        assert entry.reps == 10
        assert entry.weight_kg == 20.0
        assert entry.notes == "Felt good"
        assert entry.performed_on.isoformat() == "2026-01-15"


def test_history_add_requires_exercise_name(client):
    _signup(client)
    resp = client.post("/history/add", data={"exercise_name": ""}, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Enter an exercise name" in resp.data
    with app_module.app.app_context():
        assert ExerciseLogEntry.query.count() == 0


def test_history_add_defaults_to_today_when_date_omitted(client):
    _signup(client)
    client.post("/history/add", data={"exercise_name": "Plank"}, follow_redirects=True)
    with app_module.app.app_context():
        entry = ExerciseLogEntry.query.filter_by(exercise_name="Plank").first()
        assert entry is not None
        assert entry.performed_on is not None


def test_history_add_converts_imperial_weight_to_kg(client):
    client.set_cookie("units", "imperial")
    _signup(client)
    client.post(
        "/history/add",
        data={"exercise_name": "Bench press", "weight": "220"},
        follow_redirects=True,
    )
    with app_module.app.app_context():
        entry = ExerciseLogEntry.query.filter_by(exercise_name="Bench press").first()
        assert entry is not None
        # 220 lb ~= 99.8 kg
        assert 99 < entry.weight_kg < 100.5


def test_history_add_ignores_invalid_numeric_fields(client):
    _signup(client)
    resp = client.post(
        "/history/add",
        data={"exercise_name": "Curls", "sets": "not-a-number", "reps": "-5"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app_module.app.app_context():
        entry = ExerciseLogEntry.query.filter_by(exercise_name="Curls").first()
        assert entry is not None
        assert entry.sets is None
        assert entry.reps is None


def test_history_page_lists_own_entries(client):
    _signup(client, email="owner@example.com")
    client.post("/history/add", data={"exercise_name": "Deadlift"}, follow_redirects=True)
    resp = client.get("/history")
    assert resp.status_code == 200
    assert b"Deadlift" in resp.data


def test_history_entries_are_scoped_per_user(client):
    _signup(client, email="first@example.com")
    client.post("/history/add", data={"exercise_name": "Private Exercise"}, follow_redirects=True)
    client.get("/logout")

    _signup(client, email="second@example.com")
    resp = client.get("/history")
    assert resp.status_code == 200
    assert b"Private Exercise" not in resp.data


def test_history_delete_removes_own_entry(client):
    _signup(client)
    client.post("/history/add", data={"exercise_name": "Rows"}, follow_redirects=True)
    with app_module.app.app_context():
        entry_id = ExerciseLogEntry.query.filter_by(exercise_name="Rows").first().id

    resp = client.post(f"/history/{entry_id}/delete", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Entry deleted" in resp.data
    with app_module.app.app_context():
        assert db.session.get(ExerciseLogEntry, entry_id) is None


def test_history_delete_rejects_other_users_entry(client):
    _signup(client, email="owner2@example.com")
    client.post("/history/add", data={"exercise_name": "Lunges"}, follow_redirects=True)
    with app_module.app.app_context():
        entry_id = ExerciseLogEntry.query.filter_by(exercise_name="Lunges").first().id
    client.get("/logout")

    _signup(client, email="attacker@example.com")
    resp = client.post(f"/history/{entry_id}/delete")
    assert resp.status_code == 404

    with app_module.app.app_context():
        assert db.session.get(ExerciseLogEntry, entry_id) is not None


def test_account_shows_history_count(client):
    _signup(client, email="counter@example.com")
    client.post("/history/add", data={"exercise_name": "Squats"}, follow_redirects=True)
    client.post("/history/add", data={"exercise_name": "Push-ups"}, follow_redirects=True)

    resp = client.get("/account")
    assert resp.status_code == 200
    assert b"Workouts logged: 2" in resp.data


def test_account_export_includes_exercise_history(client):
    _signup(client, email="exporter@example.com")
    client.post("/history/add", data={"exercise_name": "Farmer carries"}, follow_redirects=True)

    resp = client.get("/account/export")
    assert resp.status_code == 200
    import json

    data = json.loads(resp.data)
    assert "exercise_history" in data
    assert data["exercise_history"][0]["exercise_name"] == "Farmer carries"


def test_account_delete_cleans_up_exercise_history(client):
    _signup(client, email="deleteme@example.com")
    client.post("/history/add", data={"exercise_name": "Squats"}, follow_redirects=True)

    with app_module.app.app_context():
        from fitafter40.core.models import User

        user_id = User.query.filter_by(email="deleteme@example.com").first().id

    resp = client.post(
        "/account/delete",
        data={"confirm_email": "deleteme@example.com", "current_password": "password123"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"account has been deleted" in resp.data
    with app_module.app.app_context():
        assert ExerciseLogEntry.query.filter_by(user_id=user_id).count() == 0
