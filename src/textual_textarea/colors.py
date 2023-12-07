from __future__ import annotations

import re
from typing import NamedTuple

from pygments.styles import get_style_by_name
from pygments.token import (
    Comment,
    Escape,
    Generic,
    Keyword,
    Literal,
    Name,
    Number,
    Operator,
    Punctuation,
    String,
    Text,
    Token,
    _TokenType,
)
from pygments.util import ClassNotFound
from rich.color import Color as RichColor
from rich.style import Style as RichStyle
from textual.color import BLACK, WHITE, Color
from textual.widgets.text_area import TextAreaTheme


def text_area_theme_from_pygments_name(pygments_name: str) -> TextAreaTheme:
    builtin = TextAreaTheme.get_builtin_theme(pygments_name)
    if builtin is not None:
        return builtin

    try:
        style = get_style_by_name(pygments_name)
    except ClassNotFound:
        return TextAreaTheme.get_builtin_theme("monokai")  # type: ignore

    bgcolor = Color.parse(style.background_color)
    contrast_text_color = bgcolor.get_contrast_text()
    fallback_style = RichStyle(color=contrast_text_color.rich_color)

    def _pick_best_analog(tokens: list[_TokenType]) -> RichStyle:
        for ttype in tokens:
            raw_style = style.styles.get(ttype)
            if raw_style is None or raw_style == "":
                continue
            else:
                rich_style = RichStyle.parse(_get_rich_markup(raw_style))
                return rich_style
        else:
            return fallback_style

    base_text_style = _pick_best_analog([Text, Token])
    selection_bgcolor = RichColor.parse(style.highlight_color)
    gutter_style = RichStyle(
        color=contrast_text_color.blend(bgcolor, 0.6).rich_color,
        bgcolor=bgcolor.blend(contrast_text_color, 0.05).rich_color,
    )
    cursor_line_gutter_style = RichStyle(
        color=contrast_text_color.blend(bgcolor, 0.5).rich_color,
        bgcolor=bgcolor.blend(contrast_text_color, 0.10).rich_color,
    )
    cursor_line_style = RichStyle(
        bgcolor=bgcolor.blend(contrast_text_color, 0.05).rich_color
    )

    theme = TextAreaTheme(
        name=pygments_name,
        base_style=RichStyle(
            color=base_text_style.color,
            bgcolor=bgcolor.rich_color,
            bold=base_text_style.bold,
            italic=base_text_style.italic,
            underline=base_text_style.underline,
        ),
        bracket_matching_style=RichStyle(bold=True),
        cursor_line_gutter_style=cursor_line_gutter_style,
        cursor_line_style=cursor_line_style,
        cursor_style=RichStyle(reverse=True),
        gutter_style=gutter_style,
        selection_style=RichStyle(bgcolor=selection_bgcolor),
        syntax_styles={
            "comment": _pick_best_analog([Comment, Token]),
            "string": _pick_best_analog([String, Literal, Token]),
            "string.documentation": _pick_best_analog(
                [Comment, String, Literal, Token]
            ),
            "string.special": _pick_best_analog(
                [Escape, String.Escape, String.Other, String, Literal, Token]
            ),
            "number": _pick_best_analog([Number, Literal, Token]),
            "float": _pick_best_analog([Number, Literal, Token]),
            "function": _pick_best_analog([Name.Function, Name, Token]),
            "function.call": _pick_best_analog([Name.Function, Name, Token]),
            "method": _pick_best_analog([Name.Function, Name, Token]),
            "method.call": _pick_best_analog([Name.Function, Name, Token]),
            "constant": _pick_best_analog([Name.Constant, Name, Token]),
            "constant.builtin": _pick_best_analog(
                [Name.Builtin, Name.Constant, Literal, Token]
            ),
            "boolean": _pick_best_analog([Name.Constant, Keyword, Name, Token]),
            "class": _pick_best_analog(
                [Name.Class, Name.Variable.Class, Name.Entity, Name, Token]
            ),
            "type": _pick_best_analog(
                [Name.Class, Name.Variable.Class, Name.Entity, Name, Token]
            ),
            "type.class": _pick_best_analog(
                [Name.Class, Name.Variable.Class, Name.Entity, Name, Token]
            ),
            "type.builtin": _pick_best_analog(
                [
                    Name.Builtin,
                    Name.Class,
                    Name.Variable.Class,
                    Name.Entity,
                    Name,
                    Token,
                ]
            ),
            "variable": _pick_best_analog(
                [Name.Variable.Instance, Name.Variable, Name.Entity, Name, Token]
            ),
            "variable.parameter": _pick_best_analog(
                [Name.Variable, Name.Entity, Name, Token]
            ),
            "operator": _pick_best_analog([Operator, Punctuation, Token]),
            "punctuation.bracket": _pick_best_analog([Punctuation, Token]),
            "punctuation.delimeter": _pick_best_analog(
                [Punctuation.Marker, Punctuation, Token]
            ),
            "keyword": _pick_best_analog(
                [
                    Keyword,
                    Generic.EmphStrong,
                    Generic.Strong,
                    Generic.Heading,
                    Name,
                    Token,
                ]
            ),
            "keyword.function": _pick_best_analog(
                [
                    Keyword,
                    Generic.EmphStrong,
                    Generic.Strong,
                    Generic.Heading,
                    Name,
                    Token,
                ]
            ),
            "keyword.return": _pick_best_analog(
                [
                    Keyword,
                    Generic.EmphStrong,
                    Generic.Strong,
                    Generic.Heading,
                    Name,
                    Token,
                ]
            ),
            "keyword.operator": _pick_best_analog([Operator, Punctuation, Token]),
            "exception": _pick_best_analog(
                [
                    Name.Function,
                    Name.Class,
                    Name.Variable.Class,
                    Name.Entity,
                    Name,
                    Token,
                ]
            ),
            "heading": _pick_best_analog(
                [Generic.Heading, Generic.EmphStrong, Generic.Strong]
            ),
            "bold": _pick_best_analog([Generic.Strong]),
            "italic": _pick_best_analog([Generic.Emph]),
        },
    )
    return theme


def _get_rich_markup(pygments_markup: str) -> str:
    def _hex_3_to_6(match: re.Match) -> str:
        """
        Replaces matches of, e.g., #fff with #ffffff
        """
        six = "".join([c * 2 for c in match.group(1)])
        return f"#{six} "

    markup = pygments_markup.replace("bg:", "on ")
    markup = markup.replace("border:", "frame ")
    markup = re.sub(r"#([0-9a-f]{3})(?:\s|$)", _hex_3_to_6, markup, flags=re.IGNORECASE)
    return markup


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
