from fitafter40.core import config
from fitafter40.utils.units import format_hydration_target, format_protein_target


def test_default_units_is_metric(client):
    resp = client.get("/tools")
    assert resp.status_code == 200
    assert b'id="bmi-height"' in resp.data
    assert b'id="bmi-weight"' in resp.data
    assert b"Height (cm)" in resp.data


def test_set_units_sets_cookie_and_redirects(client):
    resp = client.get("/set-units/imperial")
    assert resp.status_code == 302
    assert resp.headers["Set-Cookie"].startswith("units=imperial")


def test_set_units_rejects_unsupported_system(client):
    resp = client.get("/set-units/furlongs")
    assert resp.status_code == 404


def test_imperial_cookie_shows_imperial_bmi_fields(client):
    client.set_cookie("units", "imperial")
    resp = client.get("/tools")
    assert resp.status_code == 200
    assert b'id="bmi-height-ft"' in resp.data
    assert b'id="bmi-weight-lb"' in resp.data
    assert b"Height (ft, in)" in resp.data
    assert b'id="bmi-height"' not in resp.data


def test_unit_switcher_present_on_tools_page_only(client):
    # The unit toggle lives on the Tools page next to the BMI calculator
    # it actually controls, not in the site-wide nav (unlike the language
    # switcher) — it still affects the Diet Plan's numbers too, since the
    # preference itself is a site-wide cookie, but the control to change
    # it is only shown here.
    resp = client.get("/tools")
    assert b"unit-select" in resp.data

    for path in ("/", "/workouts", "/diet", "/safety", "/membership", "/contact", "/login", "/signup"):
        resp = client.get(path)
        assert b"unit-select" not in resp.data, path


def test_format_protein_target_metric():
    result = format_protein_target(1.2, 1.6, "metric")
    assert "1.2" in str(result)
    assert "1.6" in str(result)
    assert "kg" in str(result)


def test_format_protein_target_imperial_converts_kg_to_lb():
    result = str(format_protein_target(1.2, 1.6, "imperial"))
    assert "g per lb" in result
    # 1.2 kg/kg -> ~0.5 g/lb, 1.6 kg/kg -> ~0.7 g/lb
    assert "0.5" in result
    assert "0.7" in result


def test_format_hydration_target_metric():
    result = str(format_hydration_target(2.5, 3.5, "metric"))
    assert "2.5" in result
    assert "3.5" in result
    assert "L per day" in result


def test_format_hydration_target_imperial_converts_l_to_fl_oz():
    result = str(format_hydration_target(2.5, 3.5, "imperial"))
    assert "fl oz" in result
    # 2.5 L ~= 85 fl oz, 3.5 L ~= 118 fl oz
    assert "85" in result
    assert "118" in result


def test_format_hydration_target_appends_note():
    result = str(format_hydration_target(2.2, 3.0, "metric", note="— don't rely on thirst alone"))
    assert result.endswith("— don't rely on thirst alone")


def test_format_hydration_target_no_note():
    result = str(format_hydration_target(2.5, 3.5, "metric", note=None))
    assert "—" not in result


def test_unit_systems_config_has_metric_and_imperial():
    assert "metric" in config.UNIT_SYSTEMS
    assert "imperial" in config.UNIT_SYSTEMS
    assert config.DEFAULT_UNIT_SYSTEM == "metric"
