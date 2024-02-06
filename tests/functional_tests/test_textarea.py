from __future__ import annotations

from typing import List

import pytest
from textual.app import App
from textual.widgets.text_area import Selection
from textual_textarea import TextEditor


@pytest.mark.parametrize(
    "keys,text,selection,expected_text,expected_selection",
    [
        (
            ["ctrl+a"],
            "select\n foo",
            Selection(start=(1, 2), end=(1, 2)),
            "select\n foo",
            Selection(start=(0, 0), end=(1, 4)),
        ),
        (
            ["ctrl+shift+right"],
            "select\n foo",
            Selection(start=(0, 0), end=(0, 0)),
            "select\n foo",
            Selection(start=(0, 0), end=(0, 6)),
        ),
        (
            ["right"],
            "select\n foo",
            Selection(start=(0, 0), end=(0, 6)),
            "select\n foo",
            Selection(start=(1, 0), end=(1, 0)),
        ),
        (
            ["a"],
            "select\n foo",
            Selection(start=(1, 4), end=(1, 4)),
            "select\n fooa",
            Selection(start=(1, 5), end=(1, 5)),
        ),
        (
            ["a"],
            "select\n foo",
            Selection(start=(1, 0), end=(1, 4)),
            "select\na",
            Selection(start=(1, 1), end=(1, 1)),
        ),
        (
            ["enter"],
            "a\na",
            Selection(start=(1, 0), end=(1, 0)),
            "a\n\na",
            Selection(start=(2, 0), end=(2, 0)),
        ),
        (
            ["enter"],
            "a\na",
            Selection(start=(1, 1), end=(1, 1)),
            "a\na\n",
            Selection(start=(2, 0), end=(2, 0)),
        ),
        (
            ["enter", "b"],
            "a()",
            Selection(start=(0, 2), end=(0, 2)),
            "a(\n    b\n)",
            Selection(start=(1, 5), end=(1, 5)),
        ),
        (
            ["enter", "b"],
            " a()",
            Selection(start=(0, 3), end=(0, 3)),
            " a(\n    b\n )",
            Selection(start=(1, 5), end=(1, 5)),
        ),
        (
            ["delete"],
            "0\n1\n2\n3",
            Selection(start=(2, 1), end=(2, 1)),
            "0\n1\n23",
            Selection(start=(2, 1), end=(2, 1)),
        ),
        (
            ["shift+delete"],
            "0\n1\n2\n3",
            Selection(start=(2, 1), end=(2, 1)),
            "0\n1\n3",
            Selection(start=(2, 0), end=(2, 0)),
        ),
        (
            ["shift+delete"],
            "0\n1\n2\n3",
            Selection(start=(2, 0), end=(2, 1)),
            "0\n1\n\n3",
            Selection(start=(2, 0), end=(2, 0)),
        ),
        (
            ["shift+delete"],
            "0\n1\n2\n3",
            Selection(start=(3, 1), end=(3, 1)),
            "0\n1\n2",
            Selection(start=(2, 1), end=(2, 1)),
        ),
        (
            ["shift+delete"],
            "foo",
            Selection(start=(3, 1), end=(3, 1)),
            "",
            Selection(start=(0, 0), end=(0, 0)),
        ),
        (
            ["ctrl+home"],
            "foo\nbar",
            Selection(start=(1, 2), end=(1, 2)),
            "foo\nbar",
            Selection(start=(0, 0), end=(0, 0)),
        ),
        (
            ["ctrl+end"],
            "foo\nbar",
            Selection(start=(0, 1), end=(0, 1)),
            "foo\nbar",
            Selection(start=(1, 3), end=(1, 3)),
        ),
        (
            ["("],
            "foo",
            Selection(start=(0, 3), end=(0, 3)),
            "foo()",
            Selection(start=(0, 4), end=(0, 4)),
        ),
        (
            ["("],
            "foo",
            Selection(start=(0, 2), end=(0, 2)),
            "fo(o",
            Selection(start=(0, 3), end=(0, 3)),
        ),
        (
            ["("],
            "foo.",
            Selection(start=(0, 3), end=(0, 3)),
            "foo().",
            Selection(start=(0, 4), end=(0, 4)),
        ),
        (
            ["("],
            "foo-",
            Selection(start=(0, 3), end=(0, 3)),
            "foo(-",
            Selection(start=(0, 4), end=(0, 4)),
        ),
        (
            ["'"],
            "foo",
            Selection(start=(0, 3), end=(0, 3)),
            "foo'",
            Selection(start=(0, 4), end=(0, 4)),
        ),
        (
            ["'"],
            "ba  r",
            Selection(start=(0, 3), end=(0, 3)),
            "ba '' r",
            Selection(start=(0, 4), end=(0, 4)),
        ),
        (
            ["'"],
            "foo-",
            Selection(start=(0, 3), end=(0, 3)),
            "foo'-",
            Selection(start=(0, 4), end=(0, 4)),
        ),
        (
            ["'"],
            "fo--",
            Selection(start=(0, 3), end=(0, 3)),
            "fo-'-",
            Selection(start=(0, 4), end=(0, 4)),
        ),
        (
            ["'"],
            "fo-.",
            Selection(start=(0, 3), end=(0, 3)),
            "fo-''.",
            Selection(start=(0, 4), end=(0, 4)),
        ),
        (
            ["'"],
            "fo()",
            Selection(start=(0, 3), end=(0, 3)),
            "fo('')",
            Selection(start=(0, 4), end=(0, 4)),
        ),
        (
            ["tab"],
            "bar",
            Selection(start=(0, 1), end=(0, 1)),
            "b   ar",
            Selection(start=(0, 4), end=(0, 4)),
        ),
        (
            ["tab"],
            "bar",
            Selection(start=(0, 0), end=(0, 0)),
            "    bar",
            Selection(start=(0, 4), end=(0, 4)),
        ),
        (
            ["shift+tab"],
            "bar",
            Selection(start=(0, 0), end=(0, 0)),
            "bar",
            Selection(start=(0, 0), end=(0, 0)),
        ),
        (
            ["shift+tab"],
            "    bar",
            Selection(start=(0, 7), end=(0, 7)),
            "bar",
            Selection(start=(0, 3), end=(0, 3)),
        ),
        (
            ["tab"],
            "bar\n baz",
            Selection(start=(0, 2), end=(1, 1)),
            "    bar\n    baz",
            Selection(start=(0, 6), end=(1, 4)),
        ),
        (
            ["tab"],
            "bar\n baz",
            Selection(start=(0, 0), end=(1, 1)),
            "    bar\n    baz",
            Selection(start=(0, 0), end=(1, 4)),
        ),
        (
            ["shift+tab"],
            "    bar\n    baz",
            Selection(start=(0, 0), end=(1, 1)),
            "bar\nbaz",
            Selection(start=(0, 0), end=(1, 0)),
        ),
    ],
)
@pytest.mark.asyncio
async def test_keys(
    app: App,
    keys: List[str],
    text: str,
    selection: Selection,
    expected_text: str,
    expected_selection: Selection,
) -> None:
    async with app.run_test() as pilot:
        ta = app.query_one("#ta", expect_type=TextEditor)
        ta.text = text
        ta.selection = selection

        for key in keys:
            await pilot.press(key)

        assert ta.text == expected_text
        assert ta.selection == expected_selection


@pytest.mark.parametrize(
    "starting_selection,expected_clipboard,expected_paste_loc",
    [
        (Selection((0, 5), (1, 5)), "56789\n01234", (1, 5)),
        (Selection((0, 0), (1, 0)), "0123456789\n", (1, 0)),
    ],
)
@pytest.mark.asyncio
async def test_copy_paste(
    app_all_clipboards: App,
    starting_selection: Selection,
    expected_clipboard: str,
    expected_paste_loc: tuple[int, int],
) -> None:
    original_text = "0123456789\n0123456789\n0123456789"

    def eq(a: str, b: str) -> bool:
        return a.replace("\r\n", "\n") == b.replace("\r\n", "\n")

    async with app_all_clipboards.run_test() as pilot:
        ta = app_all_clipboards.query_one("#ta", expect_type=TextEditor)
        ti = ta.text_input
        ta.text = original_text
        ta.selection = starting_selection

        await pilot.press("ctrl+c")
        assert eq(ti.clipboard, expected_clipboard)
        assert ta.selection == starting_selection
        assert ta.text == original_text

        await pilot.press("ctrl+u")
        assert eq(ti.clipboard, expected_clipboard)
        assert ta.selection == Selection(starting_selection.end, starting_selection.end)
        assert ta.text == original_text

        await pilot.press("ctrl+a")
        assert ta.selection == Selection(
            (0, 0),
            (len(original_text.splitlines()) - 1, len(original_text.splitlines()[-1])),
        )
        assert eq(ti.clipboard, expected_clipboard)
        assert ta.text == original_text

        await pilot.press("ctrl+u")
        assert ta.selection == Selection(expected_paste_loc, expected_paste_loc)
        assert eq(ti.clipboard, expected_clipboard)
        assert ta.text == expected_clipboard

        await pilot.press("ctrl+a")
        await pilot.press("ctrl+x")
        assert ta.selection == Selection((0, 0), (0, 0))
        assert eq(ti.clipboard, expected_clipboard)
        assert ta.text == ""

        await pilot.press("ctrl+v")
        assert eq(ti.clipboard, expected_clipboard)
        assert ta.text == expected_clipboard
        assert ta.selection == Selection(expected_paste_loc, expected_paste_loc)


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
        assert ta.selection == Selection((0, 3), (0, 3))
        assert ti.redo_stack
        assert len(ti.redo_stack) == 1
        assert ti.redo_stack[-1].text == "foo\nbar"

        await pilot.press("ctrl+z")
        assert ti.undo_stack
        assert len(ti.undo_stack) == 1
        assert ti.undo_stack[-1].text == ""
        assert ta.text == ""
        assert ta.selection == Selection((0, 0), (0, 0))
        assert ti.redo_stack
        assert len(ti.redo_stack) == 2
        assert ti.redo_stack[-1].text == "foo"

        await pilot.press("ctrl+y")
        assert ti.undo_stack
        assert len(ti.undo_stack) == 2
        assert ti.undo_stack[-1].text == "foo"
        assert ta.text == "foo"
        assert ta.selection == Selection((0, 3), (0, 3))
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
    "start_text,insert_text,selection,expected_text",
    [
        (
            "select ",
            '"main"."drivers"."driverId"',
            Selection((0, 7), (0, 7)),
            'select "main"."drivers"."driverId"',
        ),
        (
            "select , foo",
            '"main"."drivers"."driverId"',
            Selection((0, 7), (0, 7)),
            'select "main"."drivers"."driverId", foo',
        ),
        (
            "aaa\naaa\naaa\naaa",
            "bb",
            Selection((2, 2), (2, 2)),
            "aaa\naaa\naabba\naaa",
        ),
        (
            "aaa\naaa\naaa\naaa",
            "bb",
            Selection((2, 2), (1, 1)),
            "aaa\nabba\naaa",
        ),
        (
            "01234",
            "\nabc\n",
            Selection((0, 2), (0, 2)),
            "01\nabc\n234",
        ),
    ],
)
@pytest.mark.asyncio
async def test_insert_text(
    app: App,
    start_text: str,
    insert_text: str,
    selection: Selection,
    expected_text: str,
) -> None:
    async with app.run_test() as pilot:
        ta = app.query_one("#ta", expect_type=TextEditor)
        ta.text = start_text
        ta.selection = selection
        await pilot.pause()

        ta.insert_text_at_selection(insert_text)
        await pilot.pause()

        assert ta.text == expected_text


@pytest.mark.asyncio
async def test_toggle_comment(app: App) -> None:
    async with app.run_test() as pilot:
        ta = app.query_one("#ta", expect_type=TextEditor)
        ta.text = "one\ntwo\n\nthree"
        ta.selection = Selection((0, 0), (0, 0))
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
