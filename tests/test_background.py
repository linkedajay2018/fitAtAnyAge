import os

from fitafter40.core.content import BACKGROUND_IMAGES


def test_background_images_list_is_populated():
    assert len(BACKGROUND_IMAGES) >= 3


def test_background_image_files_actually_exist_on_disk():
    backgrounds_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "backgrounds")
    for name in BACKGROUND_IMAGES:
        path = os.path.join(backgrounds_dir, name)
        assert os.path.isfile(path), f"missing background file: {name}"
        # Sanity check against an accidentally huge/unoptimized download.
        assert os.path.getsize(path) < 3 * 1024 * 1024, f"{name} is unexpectedly large"


def test_background_rotator_appears_on_every_page(client):
    for path in ("/", "/workouts", "/diet", "/tools", "/safety", "/membership", "/contact"):
        resp = client.get(path)
        assert b"bg-rotator" in resp.data, path
        assert b"bg-images-data" in resp.data, path


def test_background_image_urls_resolve(client):
    resp = client.get("/")
    assert resp.status_code == 200
    for name in BACKGROUND_IMAGES:
        img_resp = client.get(f"/static/backgrounds/{name}")
        assert img_resp.status_code == 200, name
        assert img_resp.content_type.startswith("image/")
