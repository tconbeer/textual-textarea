"""
The word and member completers stay closed inside comments and string literals.

https://github.com/tconbeer/textual-textarea/issues/341
"""

from __future__ import annotations

from typing import Callable
from unittest.mock import MagicMock

import pytest
from textual.app import App
from textual.pilot import Pilot
from textual.widgets.text_area import Selection

from textual_textarea import TextEditor


@pytest.fixture
def any_word_completer() -> MagicMock:
    """A word completer that returns a completion for every prefix."""
    mock = MagicMock()
    mock.return_value = [("completion", "completion")]
    return mock


async def settle(app: App, pilot: Pilot) -> None:
    """
    Wait for the completer (which runs in a thread) and the messages it posts.
    """
    await app.workers.wait_for_complete()
    await pilot.pause()
    await app.workers.wait_for_complete()
    await pilot.pause()


@pytest.mark.asyncio
async def test_no_completion_inside_string_literal(
    sql_app: App, word_completer: Callable[[str], list[tuple[str, str]]]
) -> None:
    """
    The bug from the issue: typing inside a string opened the word completer,
    and since the list preselects its first item, enter replaced what was typed
    with a completion.
    """
    async with sql_app.run_test() as pilot:
        ta = sql_app.query_one("#ta", expect_type=TextEditor)
        ta.word_completer = word_completer
        ta.focus()
        await pilot.pause()
        ta.text = "select "
        ta.selection = Selection((0, 7), (0, 7))
        await pilot.pause()

        await pilot.press("apostrophe")  # auto-closes to select ''
        await settle(sql_app, pilot)
        assert ta.text == "select ''"

        await pilot.press("s", "e")
        await settle(sql_app, pilot)
        assert ta.text == "select 'se'"
        assert ta.text_input is not None
        assert ta.text_input.completer_active is None
        assert ta.completion_list.is_open is False

        await pilot.press("enter")
        await settle(sql_app, pilot)
        assert ta.text == "select 'se\n'"


@pytest.mark.parametrize(
    "text,keys",
    [
        ("select 'se", ["l"]),  # unterminated string; the tree has ERROR nodes
        ("select 'sel'", ["e"]),  # cursor between the l and the closing quote
        ("select -- s", ["e"]),
        ("select 1 -- se", ["l"]),
        ("select /* s", ["e"]),  # unterminated block comment
        ("select /* se */", ["l"]),
        ("select 'a\nse'", ["l"]),  # a string that spans lines
    ],
)
@pytest.mark.asyncio
async def test_no_completion_in_no_completion_scopes(
    sql_app: App,
    word_completer: Callable[[str], list[tuple[str, str]]],
    text: str,
    keys: list[str],
) -> None:
    async with sql_app.run_test() as pilot:
        ta = sql_app.query_one("#ta", expect_type=TextEditor)
        ta.word_completer = word_completer
        lines = text.split("\n")
        ta.focus()
        await pilot.pause()
        ta.text = text
        cursor = (len(lines) - 1, len(lines[-1]))
        # a terminated literal or comment puts the cursor inside it
        if text.endswith(("'", "*/")):
            cursor = (cursor[0], cursor[1] - (1 if text.endswith("'") else 3))
        ta.selection = Selection(cursor, cursor)
        await pilot.pause()
        for key in keys:
            await pilot.press(key)
        await settle(sql_app, pilot)

        assert ta.text_input is not None
        assert ta.text_input.completer_active is None
        assert ta.completion_list.is_open is False


@pytest.mark.parametrize(
    "text",
    [
        "select se",
        "select 'abc', se",
        "select 1 -- a comment\nse",
        "select /* a comment */ se",
        "select 123",  # a number is a sql literal, but it isn't a string
        'select "se',  # a quoted identifier, not a string
    ],
)
@pytest.mark.asyncio
async def test_completion_outside_no_completion_scopes(
    sql_app: App, any_word_completer: MagicMock, text: str
) -> None:
    async with sql_app.run_test() as pilot:
        ta = sql_app.query_one("#ta", expect_type=TextEditor)
        ta.word_completer = any_word_completer
        ta.focus()
        await pilot.pause()
        lines = text.split("\n")
        ta.text = text
        cursor = (len(lines) - 1, len(lines[-1]))
        ta.selection = Selection(cursor, cursor)
        await pilot.pause()

        await pilot.press("l")
        await settle(sql_app, pilot)
        assert ta.text_input is not None
        assert ta.text_input.completer_active == "word"
        assert ta.completion_list.is_open is True


@pytest.mark.parametrize(
    "text,expected_prefix",
    [
        ('select "my col"', '"my col".'),  # a quoted identifier
        ("select `my col`", "`my col`."),
        ("select my_tbl", "my_tbl."),
    ],
)
@pytest.mark.asyncio
async def test_member_completion_after_identifiers(
    sql_app: App, member_completer: MagicMock, text: str, expected_prefix: str
) -> None:
    """
    In SQL, "my col" and `my col` are identifiers, not strings, and members
    after them are worth completing.
    """
    async with sql_app.run_test() as pilot:
        ta = sql_app.query_one("#ta", expect_type=TextEditor)
        ta.member_completer = member_completer
        ta.focus()
        await pilot.pause()
        ta.text = text
        ta.selection = Selection((0, len(text)), (0, len(text)))
        await pilot.pause()

        await pilot.press("full_stop")
        await settle(sql_app, pilot)
        assert ta.text_input is not None
        assert ta.text_input.completer_active == "member"
        member_completer.assert_called_with(expected_prefix)
        assert ta.completion_list.is_open is True


@pytest.mark.asyncio
async def test_no_member_completion_inside_string_literal(
    sql_app: App, member_completer: MagicMock
) -> None:
    async with sql_app.run_test() as pilot:
        ta = sql_app.query_one("#ta", expect_type=TextEditor)
        ta.member_completer = member_completer
        ta.focus()
        await pilot.pause()
        ta.text = "select 'my_tbl'"
        ta.selection = Selection((0, 14), (0, 14))
        await pilot.pause()

        await pilot.press("full_stop")
        await settle(sql_app, pilot)
        assert ta.text == "select 'my_tbl.'"
        assert ta.text_input is not None
        assert ta.text_input.completer_active is None
        assert ta.completion_list.is_open is False
        member_completer.assert_not_called()


@pytest.mark.asyncio
async def test_path_completion_still_works_inside_string_literal(
    sql_app: App,
) -> None:
    """
    Completing a path inside a string is the whole point of the path completer,
    so it is never suppressed.
    """
    async with sql_app.run_test() as pilot:
        ta = sql_app.query_one("#ta", expect_type=TextEditor)
        ta.focus()
        await pilot.pause()
        ta.text = "select * from read_csv('')"
        ta.selection = Selection((0, 24), (0, 24))
        await pilot.pause()

        await pilot.press("slash")
        await settle(sql_app, pilot)
        assert ta.text_input is not None
        assert ta.text_input.completer_active == "path"


@pytest.mark.asyncio
async def test_suppression_can_be_disabled(
    sql_app: App, word_completer: Callable[[str], list[tuple[str, str]]]
) -> None:
    async with sql_app.run_test() as pilot:
        ta = sql_app.query_one("#ta", expect_type=TextEditor)
        ta.word_completer = word_completer
        ta.suppress_completion_in_strings = False
        ta.suppress_completion_in_comments = False
        ta.focus()
        await pilot.pause()
        assert ta.text_input is not None
        assert ta.text_input.suppress_completion_in_strings is False
        assert ta.text_input.suppress_completion_in_comments is False

        ta.text = "select 'se'"
        ta.selection = Selection((0, 10), (0, 10))
        await pilot.pause()
        await pilot.press("l")
        await settle(sql_app, pilot)
        assert ta.text_input.completer_active == "word"
        assert ta.completion_list.is_open is True


@pytest.mark.asyncio
async def test_unconfigured_language_completes_everywhere(
    markdown_app: App, word_completer: Callable[[str], list[tuple[str, str]]]
) -> None:
    """
    A language with no declared comment or string nodes behaves exactly as it
    did before those declarations existed.
    """
    async with markdown_app.run_test() as pilot:
        ta = markdown_app.query_one("#ta", expect_type=TextEditor)
        ta.word_completer = word_completer
        ta.focus()
        await pilot.pause()
        ta.text = "'se"
        ta.selection = Selection((0, 3), (0, 3))
        await pilot.pause()

        await pilot.press("l")
        await settle(markdown_app, pilot)
        assert ta.text_input is not None
        assert ta.text_input.completer_active == "word"
        assert ta.completion_list.is_open is True


@pytest.mark.parametrize(
    "text,cursor,expected_active",
    [
        ("x = 'se'", 7, None),
        ("x = 1  # se", 11, None),
        ('x = """\nse"""', 2, None),
        ('x = f"{se}"', 9, "word"),  # an f-string's braces contain code
        ("x = se", 6, "word"),
        ('x = "se".uppe', 13, "word"),  # a member of a string literal
    ],
)
@pytest.mark.asyncio
async def test_python_scopes(
    app: App,
    any_word_completer: MagicMock,
    text: str,
    cursor: int | None,
    expected_active: str | None,
) -> None:
    async with app.run_test() as pilot:
        ta = app.query_one("#ta", expect_type=TextEditor)
        ta.word_completer = any_word_completer
        ta.focus()
        await pilot.pause()
        lines = text.split("\n")
        ta.text = text
        row = len(lines) - 1
        column = len(lines[-1]) if cursor is None else cursor
        ta.selection = Selection((row, column), (row, column))
        await pilot.pause()

        await pilot.press("l")
        await settle(app, pilot)
        assert ta.text_input is not None
        assert ta.text_input.completer_active == expected_active
        assert ta.completion_list.is_open is (expected_active is not None)
