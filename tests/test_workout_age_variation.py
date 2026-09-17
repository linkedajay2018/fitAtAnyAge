import json

from fitAtAnyAge import app as app_module
from fitAtAnyAge.core.content import AGE_GROUPS, WORKOUT_PLANS


def test_exercises_for_age_falls_back_to_base_when_no_override(client):
    plan = next(p for p in WORKOUT_PLANS if p["level_id"] == "beginner")
    result = app_module.exercises_for_age(plan, "20s")
    assert [str(e) for e in result] == [str(e) for e in plan["exercises"]]


def test_exercises_for_age_applies_override_at_correct_index(client):
    plan = next(p for p in WORKOUT_PLANS if p["level_id"] == "beginner")
    result = app_module.exercises_for_age(plan, "70s")
    override = plan["exercise_overrides_by_age"]["70s"]
    for i, exercise in enumerate(result):
        if i in override:
            assert str(exercise) == str(override[i])
        else:
            assert str(exercise) == str(plan["exercises"][i])


def test_exercises_for_age_keeps_same_length_as_base_for_every_age():
    for plan in WORKOUT_PLANS:
        base_len = len(plan["exercises"])
        for age in AGE_GROUPS:
            result = app_module.exercises_for_age(plan, age["id"])
            assert len(result) == base_len, (plan["level_id"], age["id"])


def test_active_plan_differs_between_20s_and_70s():
    # This is the actual bug report: workout content used to be identical
    # regardless of selected age. Active is where the difference should be
    # most obvious (20s gets an HIIT finisher, 70s gets reduced-load/
    # reduced-impact substitutions across several exercises).
    plan = next(p for p in WORKOUT_PLANS if p["level_id"] == "active")
    younger = [str(e) for e in app_module.exercises_for_age(plan, "20s")]
    older = [str(e) for e in app_module.exercises_for_age(plan, "70s")]
    assert younger != older


def test_workouts_page_embeds_full_age_by_level_exercise_matrix(client):
    resp = client.get("/workouts")
    assert resp.status_code == 200

    start = resp.data.index(b'id="workout-exercises-data"')
    script_start = resp.data.index(b">", start) + 1
    script_end = resp.data.index(b"</script>", script_start)
    data = json.loads(resp.data[script_start:script_end])

    level_ids = {plan["level_id"] for plan in WORKOUT_PLANS}
    age_ids = {age["id"] for age in AGE_GROUPS}
    assert set(data.keys()) == level_ids
    for level_id in level_ids:
        assert set(data[level_id].keys()) == age_ids
        for age_id in age_ids:
            exercises = data[level_id][age_id]
            assert len(exercises) == 6
            for exercise in exercises:
                assert "label" in exercise
                assert "youtube.com/results" in exercise["video_url"]


def test_workouts_page_70s_active_exercises_differ_from_20s_in_json_blob(client):
    resp = client.get("/workouts")
    start = resp.data.index(b'id="workout-exercises-data"')
    script_start = resp.data.index(b">", start) + 1
    script_end = resp.data.index(b"</script>", script_start)
    data = json.loads(resp.data[script_start:script_end])

    younger_labels = [e["label"] for e in data["active"]["20s"]]
    older_labels = [e["label"] for e in data["active"]["70s"]]
    assert younger_labels != older_labels


def test_exercise_checkbox_index_hook_present_for_progress_sync(client):
    resp = client.get("/workouts")
    assert b'data-exercise-index="0"' in resp.data
    assert b'data-exercise-index="5"' in resp.data
