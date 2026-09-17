from fitAtAnyAge.core.content import AGE_GROUPS, DIET_GUIDANCE, PROTEIN_SOURCES, SUPPLEMENT_NOTE
from fitAtAnyAge.utils.units import format_hydration_target, format_protein_target


def test_diet_guidance_covers_every_age_group():
    group_ids = {group["id"] for group in AGE_GROUPS}
    assert set(DIET_GUIDANCE.keys()) == group_ids


def test_diet_guidance_has_target_and_tips_for_every_group():
    for age_id, info in DIET_GUIDANCE.items():
        assert len(info["protein_target_kg"]) == 2, age_id
        assert info["focus"], age_id
        assert len(info["tips"]) >= 1, age_id


def test_diet_guidance_has_hydration_for_every_group():
    for age_id, info in DIET_GUIDANCE.items():
        assert len(info["hydration_target_l"]) == 2, age_id
        assert info["hydration_tip"], age_id


def test_diet_guidance_protein_and_hydration_ranges_are_low_to_high():
    for age_id, info in DIET_GUIDANCE.items():
        low, high = info["protein_target_kg"]
        assert low <= high, age_id
        low, high = info["hydration_target_l"]
        assert low <= high, age_id


def test_protein_sources_structure():
    assert len(PROTEIN_SOURCES) >= 2
    for group in PROTEIN_SOURCES:
        assert group["category"]
        assert group["icon"]
        assert len(group["foods"]) >= 1


def test_protein_sources_include_supplements():
    categories = {group["category"] for group in PROTEIN_SOURCES}
    assert "Protein Supplements" in categories
    assert SUPPLEMENT_NOTE


def test_diet_page_renders(client):
    resp = client.get("/diet")
    assert resp.status_code == 200
    assert b"Diet Plan" in resp.data
    assert b"age-selector" in resp.data
    assert b"Protein Sources" in resp.data
    assert b"not medical advice" in resp.data
    # content.py strings are flask_babel LazyStrings, which define __html__()
    # (returning the raw string) so Jinja's autoescape treats them as
    # already-safe and renders them unescaped — unlike a plain str, which
    # would get its apostrophes escaped to &#39;.
    for group in AGE_GROUPS:
        assert f"In your {group['label']}".encode() in resp.data
        info = DIET_GUIDANCE[group["id"]]
        expected_protein = format_protein_target(*info["protein_target_kg"], "metric")
        expected_hydration = format_hydration_target(
            *info["hydration_target_l"], "metric", note=info["hydration_note"]
        )
        # Unlike content.py's LazyStrings, these are plain computed str
        # (format_*_target() joins gettext() output with an f-string), so
        # Jinja's autoescape does apply here — apostrophes render as &#39;.
        assert str(expected_protein).replace("'", "&#39;").encode() in resp.data
        assert str(expected_hydration).replace("'", "&#39;").encode() in resp.data
    for group in PROTEIN_SOURCES:
        assert str(group["category"]).encode() in resp.data
        for food in group["foods"]:
            assert str(food).encode() in resp.data
    assert b"Third-party tested products" in resp.data or b"third-party tested products" in resp.data


def test_diet_page_shows_imperial_units_when_selected(client):
    client.set_cookie("units", "imperial")
    resp = client.get("/diet")
    assert resp.status_code == 200
    info = DIET_GUIDANCE["20s"]
    expected_protein = format_protein_target(*info["protein_target_kg"], "imperial")
    expected_hydration = format_hydration_target(
        *info["hydration_target_l"], "imperial", note=info["hydration_note"]
    )
    assert str(expected_protein).encode() in resp.data
    assert str(expected_hydration).encode() in resp.data
    assert b"fl oz" in resp.data
    assert b"g per lb" in resp.data


def test_diet_page_appears_in_nav(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b'href="/diet"' in resp.data
    assert b"Diet Plan" in resp.data


def test_diet_page_in_sitemap(client):
    resp = client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert b"/diet</loc>" in resp.data
