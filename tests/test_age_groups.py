from content import AGE_GROUPS, AGE_GUIDANCE, WORKOUT_PLANS


def test_age_guidance_covers_every_age_group():
    group_ids = {group["id"] for group in AGE_GROUPS}
    assert set(AGE_GUIDANCE.keys()) == group_ids


def test_age_guidance_recommended_levels_match_real_plans():
    valid_levels = {plan["level_id"] for plan in WORKOUT_PLANS}
    for age_id, info in AGE_GUIDANCE.items():
        assert info["recommended_level"] in valid_levels, age_id


def test_age_guidance_has_safety_tips_for_every_group():
    for age_id, info in AGE_GUIDANCE.items():
        assert len(info["safety_tips"]) >= 1, age_id


def test_workouts_page_includes_age_selector_and_guidance_data(client):
    resp = client.get("/workouts")
    assert resp.status_code == 200
    assert b"age-guidance-data" in resp.data
    for group in AGE_GROUPS:
        assert group["label"].encode() in resp.data
    assert b"Recommended for you" in resp.data


def test_safety_page_includes_per_decade_accordion(client):
    resp = client.get("/safety")
    assert resp.status_code == 200
    for group in AGE_GROUPS:
        assert f"In your {group['label']}".encode() in resp.data
        for tip in AGE_GUIDANCE[group["id"]]["safety_tips"]:
            # content.py strings are flask_babel LazyStrings, which define
            # __html__() (returning the raw string) so Jinja's autoescape
            # treats them as already-safe and renders them unescaped —
            # unlike a plain str, which would get its apostrophes escaped.
            assert str(tip).encode() in resp.data


def test_home_page_includes_age_selector(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"age-selector" in resp.data
    assert b"age-guidance-data" in resp.data
