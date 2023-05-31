from typing import NamedTuple

from rich.syntax import PygmentsSyntaxTheme
from textual.color import BLACK, WHITE, Color


class WidgetColors(NamedTuple):
    contrast_text_color: Color
    bgcolor: Color
    selection_bgcolor: Color

    @classmethod
    def from_theme(cls, theme: str) -> "WidgetColors":
        theme_background_style = PygmentsSyntaxTheme(theme).get_background_style()
        if (
            theme_background_style is not None
            and theme_background_style.bgcolor is not None
        ):
            t_color = Color.from_rich_color(theme_background_style.bgcolor)
            bgcolor = t_color
            contrast_text_color = t_color.get_contrast_text()
            if t_color.brightness >= 0.5:
                selection_bgcolor = t_color.darken(0.10)
            else:
                selection_bgcolor = t_color.lighten(0.10)
            return WidgetColors(contrast_text_color, bgcolor, selection_bgcolor)
        else:
            return WidgetColors(BLACK, WHITE, Color.parse("#aaaaaa"))
