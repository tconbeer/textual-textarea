from __future__ import annotations

from rich.style import Style
from textual.color import Color
from textual.theme import BUILTIN_THEMES
from textual.widgets.text_area import TextAreaTheme


def text_area_theme_from_app_theme(
    theme_name: str, css_vars: dict[str, str]
) -> TextAreaTheme | None:
    builtin = TextAreaTheme.get_builtin_theme(theme_name)
    if builtin is not None:
        return builtin

    try:
        theme = BUILTIN_THEMES[theme_name]
    except KeyError:
        return None

    background_color = Color.parse(css_vars.get("background", "#000000"))
    foreground_color = Color.parse(css_vars.get("foreground", "#FFFFFF"))
    muted = background_color.blend(foreground_color, factor=0.5)

    computed_theme = TextAreaTheme(
        name=theme_name,
        base_style=Style(color=theme.foreground, bgcolor=theme.background),
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
            "constant": theme.foreground,  # type: ignore
            "constant.builtin": theme.foreground,  # type: ignore
            "boolean": theme.accent,  # type: ignore
            "class": f"{theme.foreground} bold",  # type: ignore
            "type": f"{theme.foreground} bold",  # type: ignore
            "variable": theme.foreground,  # type: ignore
            "parameter": f"{theme.accent} bold",  # type: ignore
            "operator": theme.secondary,  # type: ignore
            "punctuation.bracket": theme.foreground,  # type: ignore
            "punctuation.delimeter": theme.foreground,  # type: ignore
            "keyword": f"{theme.primary} bold",  # type: ignore
            "keyword.function": theme.secondary,  # type: ignore
            "keyword.return": theme.primary,  # type: ignore
            "keyword.operator": theme.secondary,  # type: ignore
            "exception": theme.error,  # type: ignore
            "heading": theme.primary,  # type: ignore
            "bold": "bold",  # type: ignore
            "italic": "italic",  # type: ignore
        },
    )
    return computed_theme
