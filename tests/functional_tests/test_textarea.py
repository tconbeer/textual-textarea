from typing import List, Union

import pytest
from textual.app import App
from textual_textarea import TextArea
from textual_textarea.key_handlers import Cursor


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
        (
            ["delete"],
            ["0 ", "1 ", "2 ", "3 "],
            None,
            Cursor(2, 1),
            ["0 ", "1 ", "23 "],
            None,
            Cursor(2, 1),
        ),
        (
            ["shift+delete"],
            ["0 ", "1 ", "2 ", "3 "],
            None,
            Cursor(2, 1),
            ["0 ", "1 ", "3 "],
            None,
            Cursor(2, 0),
        ),
        (
            ["shift+delete"],
            ["0 ", "1 ", "2 ", "3 "],
            Cursor(2, 0),
            Cursor(2, 1),
            ["0 ", "1 ", " ", "3 "],
            None,
            Cursor(2, 0),
        ),
        (
            ["shift+delete"],
            ["0 ", "1 ", "2 ", "3 "],
            None,
            Cursor(3, 1),
            ["0 ", "1 ", "2 "],
            None,
            Cursor(2, 0),
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
        widget = app.query_one(TextArea)
        input = widget.text_input
        input.lines = lines.copy()
        input.selection_anchor = anchor
        input.cursor = cursor

        for key in keys:
            await pilot.press(key)

        assert input.lines == expected_lines
        assert input.selection_anchor == expected_anchor
        assert input.cursor == expected_cursor


@pytest.mark.asyncio
async def test_move_cursor(app: App) -> None:
    async with app.run_test():
        ta = app.query_one(TextArea)
        ti = ta.text_input
        ti.lines = [f"{'X' * i} " for i in range(10)]

        assert ta.cursor == Cursor(0, 0)
        for i in range(10):
            ti.move_cursor(100, i)
            assert ta.cursor == Cursor(i, i)
            ti.move_cursor(0, i)
            assert ta.cursor == Cursor(i, 0)

        ti.move_cursor(-100, -100)
        assert ta.cursor == Cursor(0, 0)

        ti.move_cursor(-10, 5)
        assert ta.cursor == Cursor(5, 0)

        ti.move_cursor(5, -5)
        assert ta.cursor == Cursor(0, 0)


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
        ti = ta.text_input
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

        await pilot.press("ctrl+v")
        assert ti.selection_anchor is None
        assert ti.cursor == Cursor(
            len(expected_clipboard) - 1, len(expected_clipboard[-1])
        )
        assert ti.clipboard == expected_clipboard
        assert ta.text == "\n".join([line.rstrip() for line in expected_clipboard])


@pytest.mark.asyncio
async def test_text_property(app: App) -> None:
    async with app.run_test():
        ta = app.query_one(TextArea)
        assert ta.text == ""
        assert ta.selected_text == ""

        ta.text = "select\nfoo"
        assert ta.text_input.lines == ["select ", "foo "]
        assert ta.selection_anchor is None
        assert ta.selected_text == ""

        # this input should be validated and cursor moved
        # to EOF
        ta.cursor = Cursor(100, 100)
        assert ta.cursor == Cursor(1, 3)
        assert ta.selection_anchor is None
        assert ta.selected_text == ""

        ta.selection_anchor = Cursor(0, 0)
        assert ta.selection_anchor == Cursor(0, 0)
        assert ta.selected_text == ta.text

        ta.selection_anchor = Cursor(0, 1)
        ta.cursor = Cursor(1, 1)
        assert ta.selected_text == "elect\nf"

        ta.text_input.lines = ["a ", " ", "b ", "c "]
        assert ta.text == "a\n\nb\nc"
        ta.cursor = Cursor(3, 0)
        assert ta.selection_anchor == Cursor(0, 1)
        assert ta.selected_text == "\n\nb\n"


@pytest.mark.asyncio
async def test_undo_redo(app: App) -> None:
    async with app.run_test() as pilot:
        ta = app.query_one(TextArea)
        ti = ta.text_input
        assert ti
        assert ti.has_focus
        assert ti.undo_stack
        assert len(ti.undo_stack) == 1
        assert ti.undo_stack[0].cursor == Cursor(0, 0)
        assert not ti.redo_stack

        for char in "foo":
            await pilot.press(char)
        await pilot.pause(0.6)
        assert ti.undo_stack
        assert len(ti.undo_stack) == 2
        assert ti.undo_stack[-1].lines == ["foo "]
        assert ti.undo_stack[-1].cursor == Cursor(0, 3)
        assert ti.undo_stack[-1].selection_anchor is None

        await pilot.press("enter")
        for char in "bar":
            await pilot.press(char)
        await pilot.pause(0.6)
        assert ti.undo_stack
        assert len(ti.undo_stack) == 3
        assert ti.undo_stack[-1].lines == ["foo ", "bar "]
        assert ti.undo_stack[-1].cursor == Cursor(1, 3)
        assert ti.undo_stack[-1].selection_anchor is None

        await pilot.press("ctrl+z")
        assert ti.undo_stack
        assert len(ti.undo_stack) == 2
        assert ti.undo_stack[-1].lines == ["foo "]
        assert ti.lines == ["foo "]
        assert ti.cursor == Cursor(0, 3)
        assert ti.redo_stack
        assert len(ti.redo_stack) == 1
        assert ti.redo_stack[-1].lines == ["foo ", "bar "]

        await pilot.press("ctrl+z")
        assert ti.undo_stack
        assert len(ti.undo_stack) == 1
        assert ti.undo_stack[-1].lines == [" "]
        assert ti.lines == [" "]
        assert ti.cursor == Cursor(0, 0)
        assert ti.redo_stack
        assert len(ti.redo_stack) == 2
        assert ti.redo_stack[-1].lines == ["foo "]

        await pilot.press("ctrl+y")
        assert ti.undo_stack
        assert len(ti.undo_stack) == 2
        assert ti.undo_stack[-1].lines == ["foo "]
        assert ti.lines == ["foo "]
        assert ti.cursor == Cursor(0, 3)
        assert ti.redo_stack
        assert len(ti.redo_stack) == 1
        assert ti.redo_stack[-1].lines == ["foo ", "bar "]

        await pilot.press("z")
        await pilot.pause(0.6)
        assert len(ti.undo_stack) == 3
        assert ti.undo_stack[-1].lines == ["fooz "]
        assert ti.lines == ["fooz "]
        assert not ti.redo_stack
