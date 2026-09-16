from __future__ import annotations

from typing import List

import pytest
from textual.app import App
from textual.events import Paste
from textual.widgets.text_area import Selection

from textual_textarea import TextEditor

ORIGINAL_TEXT = "select\n    foo,\n    bar\nfrom baz"


@pytest.mark.parametrize(
    "keys",
    [
        # paste
        ["ctrl+v"],
        ["ctrl+u"],
        ["shift+insert"],
        ["super+v"],
        # cut
        ["ctrl+x"],
        ["super+x"],
        # undo
        ["ctrl+z"],
        ["super+z"],
        # redo
        ["ctrl+y"],
        ["super+y"],
        # toggle comment
        ["ctrl+underscore"],
        # delete line
        ["shift+delete"],
        # deletes handled by textual's own actions
        ["backspace"],
        ["delete"],
        ["ctrl+backspace"],
        ["alt+backspace"],
        ["alt+delete"],
        # inserts
        ["a"],
        ["enter"],
        ["tab"],
        ["left_parenthesis"],
    ],
)
@pytest.mark.asyncio
async def test_editing_keys_do_not_mutate_a_read_only_editor(
    read_only_app: App, keys: List[str]
) -> None:
    async with read_only_app.run_test() as pilot:
        ta = read_only_app.query_one("#ta", expect_type=TextEditor)
        ti = ta.text_input
        assert ti is not None
        assert ti.read_only

        ta.text = ORIGINAL_TEXT
        ta.selection = Selection(start=(1, 4), end=(2, 7))
        ti.clipboard = "PASTED"
        # history the guards must refuse to replay: a read-only editor can
        # still be edited through the programmatic API.
        ti.insert("!", location=(0, 0))
        ti.history.checkpoint()
        expected_text = ti.text

        for key in keys:
            await pilot.press(key)
        await pilot.pause()

        assert ta.text == expected_text


@pytest.mark.asyncio
async def test_read_only_copy_still_works(read_only_app: App) -> None:
    async with read_only_app.run_test() as pilot:
        ta = read_only_app.query_one("#ta", expect_type=TextEditor)
        ti = ta.text_input
        assert ti is not None

        ta.text = ORIGINAL_TEXT
        ta.selection = Selection(start=(0, 0), end=(0, 6))

        await pilot.press("ctrl+c")
        await pilot.pause()

        assert ti.clipboard == "select"
        assert ta.text == ORIGINAL_TEXT


@pytest.mark.asyncio
async def test_terminal_paste_does_not_mutate_a_read_only_editor(
    read_only_app: App,
) -> None:
    """
    A bracketed paste from the terminal arrives as a Paste event, without
    going through the paste action, so on_paste needs its own guard.
    """
    async with read_only_app.run_test() as pilot:
        ta = read_only_app.query_one("#ta", expect_type=TextEditor)
        ti = ta.text_input
        assert ti is not None

        ta.text = ORIGINAL_TEXT
        ta.selection = Selection(start=(1, 4), end=(2, 7))
        await pilot.pause()

        ti.post_message(Paste("PASTED"))
        await pilot.pause()

        assert ta.text == ORIGINAL_TEXT


@pytest.mark.asyncio
async def test_read_only_can_be_toggled_off(read_only_app: App) -> None:
    async with read_only_app.run_test() as pilot:
        ta = read_only_app.query_one("#ta", expect_type=TextEditor)
        ti = ta.text_input
        assert ti is not None

        ta.text = ORIGINAL_TEXT
        ta.selection = Selection(start=(0, 0), end=(0, 6))
        await pilot.press("ctrl+c")
        await pilot.pause()
        assert ti.clipboard == "select"

        ta.selection = Selection(start=(0, 0), end=(0, 0))
        await pilot.press("ctrl+v")
        await pilot.pause()
        assert ta.text == ORIGINAL_TEXT

        ti.read_only = False
        await pilot.press("ctrl+v")
        await pilot.pause()
        assert ta.text == f"select{ORIGINAL_TEXT}"
