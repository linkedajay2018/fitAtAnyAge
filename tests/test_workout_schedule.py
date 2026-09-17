from fitAtAnyAge.core.content import WORKOUT_PLANS


def test_schedule_day_count_matches_days_per_week():
    for plan in WORKOUT_PLANS:
        assert len(plan["schedule"]) == plan["days_per_week"], plan["level_id"]


def test_schedule_day_numbers_are_sequential():
    for plan in WORKOUT_PLANS:
        day_numbers = [day["day_number"] for day in plan["schedule"]]
        assert day_numbers == list(range(1, len(plan["schedule"]) + 1)), plan["level_id"]


def test_schedule_covers_every_exercise_exactly_once():
    # Every exercise index (0..5) should appear in exactly one day — no
    # exercise dropped, none duplicated across days.
    for plan in WORKOUT_PLANS:
        all_indices = [i for day in plan["schedule"] for i in day["exercise_indices"]]
        assert sorted(all_indices) == list(range(len(plan["exercises"]))), plan["level_id"]


def test_schedule_indices_are_in_range():
    for plan in WORKOUT_PLANS:
        exercise_count = len(plan["exercises"])
        for day in plan["schedule"]:
            for i in day["exercise_indices"]:
                assert 0 <= i < exercise_count, (plan["level_id"], day["day_number"], i)


def test_schedule_days_have_a_focus_label():
    for plan in WORKOUT_PLANS:
        for day in plan["schedule"]:
            assert str(day["focus"]).strip(), (plan["level_id"], day["day_number"])


def test_workouts_page_renders_day_headings(client):
    resp = client.get("/workouts")
    assert resp.status_code == 200
    assert b"Day 1" in resp.data
    assert b"Day 2" in resp.data
    assert b"Day 3" in resp.data
    # Active has 5 days — the highest day count on the page.
    assert b"Day 5" in resp.data


def test_workouts_page_exercise_indices_still_span_full_range(client):
    # The day-grouping is purely a display concern — checkbox values (and
    # therefore WorkoutProgress's exercise_index) must still cover 0..5
    # for every plan, unaffected by which day an exercise is grouped under.
    resp = client.get("/workouts")
    for i in range(6):
        assert f'data-exercise-index="{i}"'.encode() in resp.data


def test_workouts_page_groups_exercises_under_correct_day(client):
    resp = client.get("/workouts")
    data = resp.data.decode()
    # Beginner's Day 1 is "Squat & Push" and should contain the squat
    # exercise (index 0) before Day 2's content begins.
    day1_start = data.index("Day 1")
    day2_start = data.index("Day 2")
    day1_section = data[day1_start:day2_start]
    assert "Bodyweight squats" in day1_section
