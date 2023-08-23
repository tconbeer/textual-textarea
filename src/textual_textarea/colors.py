from typing import NamedTuple

from pygments.styles import get_style_by_name
from pygments.util import ClassNotFound
from textual.color import BLACK, WHITE, Color


class WidgetColors(NamedTuple):
    contrast_text_color: Color
    bgcolor: Color
    selection_bgcolor: Color

    @classmethod
    def from_theme(cls, theme: str) -> "WidgetColors":
        try:
            style = get_style_by_name(theme)
        except ClassNotFound:
            return WidgetColors(BLACK, WHITE, Color.parse("#aaaaaa"))
        bgcolor = Color.parse(style.background_color)
        contrast_text_color = bgcolor.get_contrast_text()
        selection_bgcolor = Color.parse(style.highlight_color)
        return WidgetColors(contrast_text_color, bgcolor, selection_bgcolor)
