from typing import List, Union

import pytest
from textual.app import App
from textual.widgets.text_area import Selection
from textual_textarea import TextEditor
from textual_textarea.key_handlers import Cursor
from textual_textarea.serde import deserialize_lines, serialize_lines


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
            ["enter", "b"],
            ["a() "],
            None,
            Cursor(0, 2),
            ["a( ", "    b ", ") "],
            None,
            Cursor(1, 5),
        ),
        (
            ["enter", "b"],
            [" a() "],
            None,
            Cursor(0, 3),
            [" a( ", "    b ", " ) "],
            None,
            Cursor(1, 5),
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
            Cursor(2, 1),
        ),
        (
            ["shift+delete"],
            ["foo "],
            None,
            Cursor(3, 1),
            [" "],
            None,
            Cursor(0, 0),
        ),
        (
            ["ctrl+home"],
            ["foo ", "bar"],
            None,
            Cursor(1, 2),
            ["foo ", "bar"],
            None,
            Cursor(0, 0),
        ),
        (
            ["ctrl+end"],
            ["foo ", "bar"],
            None,
            Cursor(0, 1),
            ["foo ", "bar"],
            None,
            Cursor(1, 3),
        ),
        (
            ["("],
            ["foo "],
            None,
            Cursor(0, 3),
            ["foo() "],
            None,
            Cursor(0, 4),
        ),
        (
            ["("],
            ["foo "],
            None,
            Cursor(0, 2),
            ["fo(o "],
            None,
            Cursor(0, 3),
        ),
        (
            ["("],
            ["foo. "],
            None,
            Cursor(0, 3),
            ["foo(). "],
            None,
            Cursor(0, 4),
        ),
        (
            ["("],
            ["foo- "],
            None,
            Cursor(0, 3),
            ["foo(- "],
            None,
            Cursor(0, 4),
        ),
        (
            ["'"],
            ["foo "],
            None,
            Cursor(0, 3),
            ["foo' "],
            None,
            Cursor(0, 4),
        ),
        (
            ["'"],
            ["ba  r "],
            None,
            Cursor(0, 3),
            ["ba '' r "],
            None,
            Cursor(0, 4),
        ),
        (
            ["'"],
            ["foo- "],
            None,
            Cursor(0, 3),
            ["foo'- "],
            None,
            Cursor(0, 4),
        ),
        (
            ["'"],
            ["fo-- "],
            None,
            Cursor(0, 3),
            ["fo-'- "],
            None,
            Cursor(0, 4),
        ),
        (
            ["'"],
            ["fo-. "],
            None,
            Cursor(0, 3),
            ["fo-''. "],
            None,
            Cursor(0, 4),
        ),
        (
            ["'"],
            ["fo() "],
            None,
            Cursor(0, 3),
            ["fo('') "],
            None,
            Cursor(0, 4),
        ),
        (
            ["tab"],
            ["bar "],
            None,
            Cursor(0, 1),
            ["b   ar "],
            None,
            Cursor(0, 4),
        ),
        (
            ["tab"],
            ["bar "],
            None,
            Cursor(0, 0),
            ["    bar "],
            None,
            Cursor(0, 4),
        ),
        (
            ["shift+tab"],
            ["bar "],
            None,
            Cursor(0, 0),
            ["bar "],
            None,
            Cursor(0, 0),
        ),
        (
            ["shift+tab"],
            ["    bar "],
            None,
            Cursor(0, 7),
            ["bar "],
            None,
            Cursor(0, 3),
        ),
        (
            ["tab"],
            ["bar ", " baz "],
            Cursor(0, 2),
            Cursor(1, 1),
            ["    bar ", "    baz "],
            Cursor(0, 6),
            Cursor(1, 4),
        ),
        (
            ["tab"],
            ["bar ", " baz "],
            Cursor(0, 0),
            Cursor(1, 1),
            ["    bar ", "    baz "],
            Cursor(0, 0),
            Cursor(1, 4),
        ),
        (
            ["shift+tab"],
            ["    bar ", "    baz "],
            Cursor(0, 0),
            Cursor(1, 1),
            ["bar ", "baz "],
            Cursor(0, 0),
            Cursor(1, 0),
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
        ta = app.query_one("#ta", expect_type=TextEditor)
        ta.text = serialize_lines(lines)
        ta.cursor = cursor
        ta.selection_anchor = anchor

        for key in keys:
            await pilot.press(key)

        assert ta.text == serialize_lines(expected_lines)
        assert ta.selection_anchor == expected_anchor
        assert ta.cursor == expected_cursor


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

    def _maybe_split(raw: Union[str, List[str]]) -> List[str]:
        if isinstance(raw, str):
            return deserialize_lines(raw, trim=True)
        else:
            return raw

    async with app_all_clipboards.run_test() as pilot:
        ta = app_all_clipboards.query_one("#ta", expect_type=TextEditor)
        ti = ta.text_input
        ta.text = original_text
        ta.cursor = starting_cursor
        ta.selection_anchor = starting_anchor

        await pilot.press("ctrl+c")
        assert _maybe_split(ti.clipboard) == expected_clipboard
        assert ta.selection_anchor == starting_anchor
        assert ta.cursor == starting_cursor
        assert ta.text == original_text

        await pilot.press("ctrl+u")
        assert _maybe_split(ti.clipboard) == expected_clipboard
        assert ta.selection_anchor is None
        assert ta.cursor == starting_cursor
        assert ta.text == original_text

        await pilot.press("ctrl+a")
        assert ta.selection_anchor == Cursor(0, 0)
        assert ta.cursor == Cursor(
            len(original_text.splitlines()) - 1, len(original_text.splitlines()[-1])
        )
        assert _maybe_split(ti.clipboard) == expected_clipboard
        assert ta.text == original_text

        await pilot.press("ctrl+u")
        assert ta.selection_anchor is None
        assert ta.cursor == Cursor(
            len(expected_clipboard) - 1, len(expected_clipboard[-1])
        )
        assert _maybe_split(ti.clipboard) == expected_clipboard
        assert ta.text == "\n".join([line.strip() for line in expected_clipboard])

        await pilot.press("ctrl+a")
        await pilot.press("ctrl+x")
        assert ta.selection_anchor is None
        assert ta.cursor == Cursor(0, 0)
        assert _maybe_split(ti.clipboard) == expected_clipboard
        assert ta.text == ""

        await pilot.press("ctrl+v")
        assert ta.selection_anchor is None
        assert _maybe_split(ti.clipboard) == expected_clipboard
        assert ta.text == "\n".join([line.rstrip() for line in expected_clipboard])
        assert ta.cursor == Cursor(
            len(expected_clipboard) - 1, len(expected_clipboard[-1])
        )


@pytest.mark.asyncio
async def test_undo_redo(app: App) -> None:
    async with app.run_test() as pilot:
        ta = app.query_one("#ta", expect_type=TextEditor)
        ti = ta.text_input
        assert ti
        assert ti.has_focus
        assert ti.undo_stack
        assert len(ti.undo_stack) == 1
        assert ti.undo_stack[0].selection == Selection((0, 0), (0, 0))
        assert not ti.redo_stack

        for char in "foo":
            await pilot.press(char)
        await pilot.pause(0.6)
        assert ti.undo_stack
        assert len(ti.undo_stack) == 2
        assert ti.undo_stack[-1].text == "foo"
        assert ti.undo_stack[-1].selection == Selection((0, 3), (0, 3))

        await pilot.press("enter")
        for char in "bar":
            await pilot.press(char)
        await pilot.pause(0.6)
        assert ti.undo_stack
        assert len(ti.undo_stack) == 3
        assert ti.undo_stack[-1].text == "foo\nbar"
        assert ti.undo_stack[-1].selection == Selection((1, 3), (1, 3))

        await pilot.press("ctrl+z")
        assert ti.undo_stack
        assert len(ti.undo_stack) == 2
        assert ti.undo_stack[-1].text == "foo"
        assert ta.text == "foo"
        assert ta.cursor == Cursor(0, 3)
        assert ti.redo_stack
        assert len(ti.redo_stack) == 1
        assert ti.redo_stack[-1].text == "foo\nbar"

        await pilot.press("ctrl+z")
        assert ti.undo_stack
        assert len(ti.undo_stack) == 1
        assert ti.undo_stack[-1].text == ""
        assert ta.text == ""
        assert ta.cursor == Cursor(0, 0)
        assert ti.redo_stack
        assert len(ti.redo_stack) == 2
        assert ti.redo_stack[-1].text == "foo"

        await pilot.press("ctrl+y")
        assert ti.undo_stack
        assert len(ti.undo_stack) == 2
        assert ti.undo_stack[-1].text == "foo"
        assert ta.text == "foo"
        assert ta.cursor == Cursor(0, 3)
        assert ti.redo_stack
        assert len(ti.redo_stack) == 1
        assert ti.redo_stack[-1].text == "foo\nbar"

        await pilot.press("z")
        await pilot.pause(0.6)
        assert len(ti.undo_stack) == 3
        assert ti.undo_stack[-1].text == "fooz"
        assert ta.text == "fooz"
        assert not ti.redo_stack


@pytest.mark.parametrize(
    "start_text,insert_text,cursor,selection,expected_text",
    [
        (
            "select ",
            '"main"."drivers"."driverId"',
            Cursor(0, 7),
            None,
            'select "main"."drivers"."driverId"',
        ),
        (
            "select , foo",
            '"main"."drivers"."driverId"',
            Cursor(0, 7),
            None,
            'select "main"."drivers"."driverId", foo',
        ),
        ("aaa\naaa\naaa\naaa", "bb", Cursor(2, 2), None, "aaa\naaa\naabba\naaa"),
        ("aaa\naaa\naaa\naaa", "bb", Cursor(2, 2), Cursor(1, 1), "aaa\nabba\naaa"),
        ("01234", "\nabc\n", Cursor(lno=0, pos=2), None, "01\nabc\n234"),
    ],
)
@pytest.mark.asyncio
async def test_insert_text(
    app: App,
    start_text: str,
    insert_text: str,
    cursor: Cursor,
    selection: Union[Cursor, None],
    expected_text: str,
) -> None:
    async with app.run_test() as pilot:
        ta = app.query_one("#ta", expect_type=TextEditor)
        ta.text = start_text
        ta.cursor = cursor
        ta.selection_anchor = selection
        await pilot.pause()

        ta.insert_text_at_selection(insert_text)
        await pilot.pause()

        assert ta.text == expected_text


@pytest.mark.asyncio
async def test_toggle_comment(app: App) -> None:
    async with app.run_test() as pilot:
        ta = app.query_one("#ta", expect_type=TextEditor)
        ta.text = "one\ntwo\n\nthree"
        ta.cursor = Cursor(0, 0)
        await pilot.pause()

        await pilot.press("ctrl+underscore")
        assert ta.text == "# one\ntwo\n\nthree"

        await pilot.press("down")
        await pilot.press("ctrl+underscore")
        assert ta.text == "# one\n# two\n\nthree"

        await pilot.press("ctrl+a")
        await pilot.press("ctrl+underscore")
        assert ta.text == "# # one\n# # two\n\n# three"

        await pilot.press("ctrl+underscore")
        assert ta.text == "# one\n# two\n\nthree"

        await pilot.press("up")
        await pilot.press("up")
        await pilot.press("ctrl+underscore")
        assert ta.text == "# one\ntwo\n\nthree"

        await pilot.press("shift+down")
        await pilot.press("shift+down")
        await pilot.press("ctrl+underscore")
        assert ta.text == "# one\n# two\n\n# three"

        await pilot.press("ctrl+a")
        await pilot.press("ctrl+underscore")
        assert ta.text == "one\ntwo\n\nthree"
