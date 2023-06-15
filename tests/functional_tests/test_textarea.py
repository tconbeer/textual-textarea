from typing import List, Union

import pytest
from textual.app import App
from textual_textarea.key_handlers import Cursor
from textual_textarea.textarea import TextArea, TextInput


@pytest.mark.parametrize(
    "keys,lines,anchor,cursor,expected_lines,expected_anchor,expected_cursor",
    [
        (
            ["ctrl+a"],
            ["select ", " foo "],
            None,
            Cursor(1, 2),
            None,
            Cursor(0, 0),
            Cursor(1, 4),
        ),
        (
            ["ctrl+shift+right"],
            ["select ", " foo "],
            None,
            Cursor(0, 0),
            None,
            Cursor(0, 0),
            Cursor(0, 6),
        ),
        (
            ["right"],
            ["select ", " foo "],
            Cursor(0, 0),
            Cursor(0, 6),
            None,
            None,
            Cursor(1, 0),
        ),
        (
            ["a"],
            ["select ", " foo "],
            None,
            Cursor(1, 4),
            ["select ", " fooa "],
            None,
            Cursor(1, 5),
        ),
        (
            ["a"],
            ["select ", " foo "],
            Cursor(1, 0),
            Cursor(1, 4),
            ["select ", "a "],
            None,
            Cursor(1, 1),
        ),
        (
            ["enter"],
            ["a ", "a "],
            None,
            Cursor(1, 0),
            ["a ", " ", "a "],
            None,
            Cursor(2, 0),
        ),
        (
            ["enter"],
            ["a ", "a "],
            None,
            Cursor(1, 1),
            ["a ", "a ", " "],
            None,
            Cursor(2, 0),
        ),
        (
            ["enter"],
            ["a() "],
            None,
            Cursor(0, 2),
            ["a( ", "     ", ") "],
            None,
            Cursor(1, 4),
        ),
        (
            ["enter"],
            [" a() "],
            None,
            Cursor(0, 3),
            [" a( ", "     ", " ) "],
            None,
            Cursor(1, 4),
        ),
    ],
)
@pytest.mark.asyncio
async def test_keys(
    app: App,
    keys: List[str],
    lines: List[str],
    anchor: Union[Cursor, None],
    cursor: Cursor,
    expected_lines: Union[List[str], None],
    expected_anchor: Union[Cursor, None],
    expected_cursor: Cursor,
) -> None:
    if expected_lines is None:
        expected_lines = lines

    async with app.run_test() as pilot:
        widget = app.query_one(TextInput)
        widget.lines = lines.copy()
        widget.selection_anchor = anchor
        widget.cursor = cursor

        for key in keys:
            await pilot.press(key)

        assert widget.lines == expected_lines
        assert widget.selection_anchor == expected_anchor
        assert widget.cursor == expected_cursor


@pytest.mark.parametrize(
    "starting_anchor,starting_cursor,expected_clipboard",
    [
        (Cursor(0, 5), Cursor(1, 5), ["56789 ", "01234"]),
        (Cursor(0, 0), Cursor(1, 0), ["0123456789 ", ""]),
    ],
)
@pytest.mark.asyncio
async def test_copy_paste(
    app_all_clipboards: App,
    starting_anchor: Cursor,
    starting_cursor: Cursor,
    expected_clipboard: List[str],
) -> None:
    original_text = "0123456789\n0123456789\n0123456789"

    async with app_all_clipboards.run_test() as pilot:
        ta = app_all_clipboards.query_one(TextArea)
        ti = app_all_clipboards.query_one(TextInput)
        ta.text = original_text
        ti.selection_anchor = starting_anchor
        ti.cursor = starting_cursor

        await pilot.press("ctrl+c")
        assert ti.clipboard == expected_clipboard
        assert ti.selection_anchor == starting_anchor
        assert ti.cursor == starting_cursor
        assert ta.text == original_text

        await pilot.press("ctrl+u")
        assert ti.clipboard == expected_clipboard
        assert ti.selection_anchor is None
        assert ti.cursor == starting_cursor
        assert ta.text == original_text

        await pilot.press("ctrl+a")
        assert ti.selection_anchor == Cursor(0, 0)
        assert ti.cursor == Cursor(
            len(original_text.splitlines()) - 1, len(original_text.splitlines()[-1])
        )
        assert ti.clipboard == expected_clipboard
        assert ta.text == original_text

        await pilot.press("ctrl+u")
        assert ti.selection_anchor is None
        assert ti.cursor == Cursor(
            len(expected_clipboard) - 1, len(expected_clipboard[-1])
        )
        assert ti.clipboard == expected_clipboard
        assert ta.text == "\n".join([line.strip() for line in expected_clipboard])

        await pilot.press("ctrl+a")
        await pilot.press("ctrl+x")
        assert ti.selection_anchor is None
        assert ti.cursor == Cursor(0, 0)
        assert ti.clipboard == expected_clipboard
        assert ta.text == ""

        await pilot.press("ctrl+u")
        assert ti.selection_anchor is None
        assert ti.cursor == Cursor(
            len(expected_clipboard) - 1, len(expected_clipboard[-1])
        )
        assert ti.clipboard == expected_clipboard
        assert ta.text == "\n".join([line.rstrip() for line in expected_clipboard])
