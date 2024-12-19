from __future__ import annotations

from rich.style import Style
from textual.color import Color
from textual.theme import Theme
from textual.widgets.text_area import TextAreaTheme


def text_area_theme_from_app_theme(
    theme_name: str, theme: Theme, css_vars: dict[str, str]
) -> TextAreaTheme:
    builtin = TextAreaTheme.get_builtin_theme(theme_name)
    if builtin is not None:
        return builtin

    if "background" in css_vars:
        background_color = Color.parse(
            css_vars.get("background", "#000000" if theme.dark else "#FFFFFF")
        )
        foreground_color = Color.parse(
            css_vars.get("foreground", background_color.inverse)
        )
    else:
        foreground_color = Color.parse(
            css_vars.get("foreground", "#FFFFFF" if theme.dark else "#000000")
        )
        background_color = foreground_color.inverse

    muted = background_color.blend(foreground_color, factor=0.5)

    computed_theme = TextAreaTheme(
        name=theme_name,
        base_style=Style(
            color=foreground_color.rich_color, bgcolor=background_color.rich_color
        ),
        syntax_styles={
            "comment": muted.hex,  # type: ignore
            "string": theme.accent,  # type: ignore
            "string.documentation": muted.hex,  # type: ignore
            "string.special": theme.accent,  # type: ignore
            "number": theme.accent,  # type: ignore
            "float": theme.accent,  # type: ignore
            "function": theme.secondary,  # type: ignore
            "function.call": theme.secondary,  # type: ignore
            "method": theme.secondary,  # type: ignore
            "method.call": theme.secondary,  # type: ignore
            "constant": foreground_color.hex,  # type: ignore
            "constant.builtin": foreground_color.hex,  # type: ignore
            "boolean": theme.accent,  # type: ignore
            "class": f"{foreground_color.hex} bold",  # type: ignore
            "type": f"{foreground_color.hex} bold",  # type: ignore
            "variable": foreground_color.hex,  # type: ignore
            "parameter": f"{theme.accent} bold",  # type: ignore
            "operator": theme.secondary,  # type: ignore
            "punctuation.bracket": foreground_color.hex,  # type: ignore
            "punctuation.delimeter": foreground_color.hex,  # type: ignore
            "keyword": f"{theme.primary} bold",  # type: ignore
            "keyword.function": theme.secondary,  # type: ignore
            "keyword.return": theme.primary,  # type: ignore
            "keyword.operator": f"{theme.primary} bold",  # type: ignore
            "exception": theme.error,  # type: ignore
            "heading": theme.primary,  # type: ignore
            "bold": "bold",  # type: ignore
            "italic": "italic",  # type: ignore
        },
    )
    return computed_theme
