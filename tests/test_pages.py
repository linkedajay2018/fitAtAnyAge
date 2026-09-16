def test_index_page(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"FitAtAnyAge" in resp.data


def test_workouts_page_lists_plans_and_video_links(client):
    resp = client.get("/workouts")
    assert resp.status_code == 200
    assert b"Beginner" in resp.data
    assert b"Intermediate" in resp.data
    assert b"Active" in resp.data
    assert b"youtube.com/results" in resp.data


def test_tools_page_has_bmi_calculator(client):
    resp = client.get("/tools")
    assert resp.status_code == 200
    assert b"BMI Calculator" in resp.data


def test_bmi_calculator_has_optional_age_and_sex_fields(client):
    resp = client.get("/tools")
    assert resp.status_code == 200
    assert b'id="bmi-age"' in resp.data
    assert b'id="bmi-sex"' in resp.data
    assert b'value="male"' in resp.data
    assert b'value="female"' in resp.data


def test_tools_page_has_heart_rate_calculator(client):
    resp = client.get("/tools")
    assert resp.status_code == 200
    assert b"Target Heart Rate Zones" in resp.data
    assert b'id="hr-age"' in resp.data


def test_tools_page_has_calorie_calculator(client):
    resp = client.get("/tools")
    assert resp.status_code == 200
    assert b"Daily Calorie Needs" in resp.data
    assert b'id="tdee-height"' in resp.data
    assert b'id="tdee-weight"' in resp.data
    assert b'id="tdee-age"' in resp.data
    assert b'id="tdee-activity"' in resp.data


def test_tools_page_has_one_rep_max_calculator(client):
    resp = client.get("/tools")
    assert resp.status_code == 200
    assert b"1-Rep Max Estimator" in resp.data
    assert b'id="orm-weight"' in resp.data
    assert b'id="orm-reps"' in resp.data


def test_tools_page_has_waist_hip_ratio_calculator(client):
    resp = client.get("/tools")
    assert resp.status_code == 200
    assert b"Waist-to-Hip Ratio" in resp.data
    assert b'id="whr-waist"' in resp.data
    assert b'id="whr-hip"' in resp.data


def test_tools_page_uses_imperial_fields_for_new_calculators_too(client):
    client.set_cookie("units", "imperial")
    resp = client.get("/tools")
    assert resp.status_code == 200
    assert b'id="tdee-height-ft"' in resp.data
    assert b'id="tdee-weight-lb"' in resp.data
    assert b"Weight Lifted (lb)" in resp.data
    assert b"Waist (in)" in resp.data


def test_safety_page_lists_tips(client):
    resp = client.get("/safety")
    assert resp.status_code == 200
    assert b"warm up" in resp.data


def test_unknown_route_is_404(client):
    resp = client.get("/does-not-exist")
    assert resp.status_code == 404
