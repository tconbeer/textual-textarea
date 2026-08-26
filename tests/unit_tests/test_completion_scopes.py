from __future__ import annotations

import pytest

from textual_textarea.completion_scopes import is_string, scan_for_unterminated_scope


@pytest.mark.parametrize(
    "language,opening_characters,expected",
    [
        ("sql", "'abc'", True),
        ("sql", "N'abc'", True),  # a prefixed string literal
        ("sql", "E'abc'", True),
        ("sql", '"my col"', False),  # a quoted identifier, not a string
        ("sql", "`my col`", False),
        ("sql", "123", False),  # tree-sitter-sql parses a number to a literal
        ("python", "'abc'", True),
        ("python", '"""abc', True),
        ("python", 'rb"abc"', True),
        ("rust", 'br#"abc', True),
        ("javascript", "`abc`", True),
        ("markdown", "'abc'", True),  # no declared quotes; every node counts
    ],
)
def test_is_string(language: str, opening_characters: str, expected: bool) -> None:
    assert is_string(language, opening_characters) is expected


@pytest.mark.parametrize(
    "language,text,expected",
    [
        ("sql", "select 'ab", "string"),
        ("sql", "select 'ab'", None),
        ("sql", "select 'it''s ab", "string"),
        ("sql", "select 'it''s'", None),
        ("sql", 'select "my col", ab', None),  # a quoted identifier
        ("sql", "select $1, ab", None),  # a placeholder, not a dollar quote
        ("sql", "select 1 -- ab", "comment"),
        ("sql", "select 1 -- don't ab", "comment"),  # the quote is commented out
        ("sql", "select '-- not a comment", "string"),
        ("sql", "select /* ab", "comment"),
        ("sql", "select /* ab */ cd", None),
        ("sql", "select /* ab */ 'cd", "string"),
        ("python", "x = 'ab", "string"),
        ("python", "x = 'a\\'b", "string"),  # an escaped quote
        ("python", "x = 1  # ab", "comment"),
        ("python", "x = 1", None),
        ("python", "x = '#ab", "string"),
        ("markdown", "'ab", None),  # an unconfigured language never suppresses
    ],
)
def test_scan_for_unterminated_scope(
    language: str, text: str, expected: str | None
) -> None:
    assert scan_for_unterminated_scope(language, text) == expected
