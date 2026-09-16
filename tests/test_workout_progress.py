from unittest.mock import patch

import app as app_module
from content import WORKOUT_PLANS
from models import WorkoutProgress, db

from helpers import signup


def test_api_get_requires_login(client):
    resp = client.get("/api/workout-progress")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_api_post_requires_login(client):
    resp = client.post("/api/workout-progress", json={"level_id": "beginner", "exercise_index": 0, "completed": True})
    assert resp.status_code == 302


def test_api_get_returns_empty_for_new_user(client):
    with patch("app.send_verification_email"):
        signup(client)
    resp = client.get("/api/workout-progress")
    assert resp.status_code == 200
    assert resp.get_json() == {}


def test_api_post_saves_and_get_reflects_it(client):
    with patch("app.send_verification_email"):
        signup(client)

    resp = client.post(
        "/api/workout-progress",
        json={"level_id": "beginner", "exercise_index": 2, "completed": True},
    )
    assert resp.status_code == 200

    resp = client.get("/api/workout-progress")
    data = resp.get_json()
    assert data == {"beginner": {"2": True}}


def test_api_post_toggling_off_removes_from_get(client):
    with patch("app.send_verification_email"):
        signup(client)

    client.post("/api/workout-progress", json={"level_id": "active", "exercise_index": 0, "completed": True})
    client.post("/api/workout-progress", json={"level_id": "active", "exercise_index": 0, "completed": False})

    resp = client.get("/api/workout-progress")
    assert resp.get_json() == {}


def test_api_post_rejects_invalid_level_id(client):
    with patch("app.send_verification_email"):
        signup(client)
    resp = client.post(
        "/api/workout-progress",
        json={"level_id": "not-a-real-level", "exercise_index": 0, "completed": True},
    )
    assert resp.status_code == 400


def test_api_post_rejects_non_integer_exercise_index(client):
    with patch("app.send_verification_email"):
        signup(client)
    resp = client.post(
        "/api/workout-progress",
        json={"level_id": "beginner", "exercise_index": "not-a-number", "completed": True},
    )
    assert resp.status_code == 400


def test_progress_is_scoped_per_user(client):
    with patch("app.send_verification_email"):
        signup(client, email="first@example.com")
    client.post("/api/workout-progress", json={"level_id": "beginner", "exercise_index": 0, "completed": True})
    client.get("/logout")

    with patch("app.send_verification_email"):
        signup(client, email="second@example.com")
    resp = client.get("/api/workout-progress")
    assert resp.get_json() == {}


def test_workouts_page_checkboxes_use_stable_index_not_label(client):
    resp = client.get("/workouts")
    assert resp.status_code == 200
    assert b'<input type="checkbox" value="0">' in resp.data


def test_account_shows_no_progress_message_when_empty(client):
    with patch("app.send_verification_email"):
        signup(client)
    resp = client.get("/account")
    assert resp.status_code == 200
    assert b"No completed exercises yet" in resp.data


def test_account_shows_progress_summary(client):
    with patch("app.send_verification_email"):
        signup(client)
    client.post("/api/workout-progress", json={"level_id": "beginner", "exercise_index": 0, "completed": True})
    client.post("/api/workout-progress", json={"level_id": "beginner", "exercise_index": 1, "completed": True})

    resp = client.get("/account")
    assert resp.status_code == 200
    total = sum(len(plan["exercises"]) for plan in WORKOUT_PLANS)
    assert f"2 of {total}".encode() in resp.data


def test_account_delete_cleans_up_workout_progress(client):
    with patch("app.send_verification_email"):
        signup(client, email="deleteprogress@example.com", password="password123")

    with app_module.app.app_context():
        from models import User

        user = User.query.filter_by(email="deleteprogress@example.com").first()
        user_id = user.id

    client.post("/api/workout-progress", json={"level_id": "beginner", "exercise_index": 0, "completed": True})

    client.post(
        "/account/delete",
        data={"confirm_email": "deleteprogress@example.com", "current_password": "password123"},
        follow_redirects=True,
    )

    with app_module.app.app_context():
        assert WorkoutProgress.query.filter_by(user_id=user_id).count() == 0
