import pytest
from pygments.styles import get_all_styles
from textual_textarea.colors import text_area_theme_from_pygments_name


@pytest.mark.parametrize("style", get_all_styles())
def test_can_build_theme(style: str) -> None:
    theme = text_area_theme_from_pygments_name(style)
    assert theme
    assert theme.base_style is not None
    assert theme.base_style.bgcolor is not None
    assert theme.base_style.color is not None
    assert theme.base_style.color != theme.base_style.bgcolor


def test_does_not_raise_on_bad_theme() -> None:
    theme = text_area_theme_from_pygments_name("not a real style")
    assert theme
