import config


def test_robots_txt(client):
    resp = client.get("/robots.txt")
    assert resp.status_code == 200
    assert resp.content_type.startswith("text/plain")
    assert b"User-agent: *" in resp.data
    assert b"Sitemap:" in resp.data
    assert b"/sitemap.xml" in resp.data


def test_sitemap_xml_lists_public_pages(client):
    resp = client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert resp.content_type.startswith("application/xml")
    assert b"<urlset" in resp.data
    for path in ("/", "/workouts", "/tools", "/safety", "/membership", "/contact"):
        assert path.encode() in resp.data


def test_404_page_is_custom_and_correct_status(client):
    resp = client.get("/this-page-does-not-exist")
    assert resp.status_code == 404
    assert b"Page Not Found" in resp.data


def test_base_template_includes_meta_description_and_canonical(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b'name="description"' in resp.data
    assert b'rel="canonical"' in resp.data
    assert b"application/ld+json" in resp.data


def test_config_has_sensible_defaults():
    assert config.SITE_NAME
    assert config.SITE_DESCRIPTION
    assert config.DOMAIN
    assert config.STRIPE_CONFIGURED is False
    assert config.UPI_CONFIGURED is False
