"""Lightweight tests for the visual theme's safe background behaviour."""

from ui_styles import background_image_data, build_global_css


def test_missing_background_uses_gradient(tmp_path):
    background_image_data.cache_clear()
    assert background_image_data(tmp_path / "missing.jpg") is None
    css = build_global_css(None)
    assert "radial-gradient" in css
    assert "url('None')" not in css


def test_existing_background_is_encoded_once(tmp_path):
    image = tmp_path / "stadium-background.jpg"
    image.write_bytes(b"small-test-image")
    background_image_data.cache_clear()
    encoded = background_image_data(image)
    assert encoded.startswith("data:image/jpeg;base64,")
    assert encoded in build_global_css(encoded)
