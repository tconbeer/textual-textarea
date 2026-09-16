from __future__ import annotations

from typing import List

import pytest
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.events import Paste
from textual.widgets import Input
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


@pytest.mark.asyncio
async def test_show_cursor_is_forwarded_to_the_text_area(
    app: App, preview_app: App
) -> None:
    async with app.run_test():
        ti = app.query_one("#ta", expect_type=TextEditor).text_input
        assert ti is not None
        assert ti.show_cursor is True

    async with preview_app.run_test() as pilot:
        ta = preview_app.query_one("#ta", expect_type=TextEditor)
        ti = ta.text_input
        assert ti is not None
        assert ti.show_cursor is False
        assert ta.show_cursor is False

        # and it can still be toggled after mount, through the editor
        ta.show_cursor = True
        await pilot.pause()
        assert ti.show_cursor is True
        assert ta.show_cursor is True


@pytest.mark.parametrize(
    "key",
    ["ctrl+s", "ctrl+o", "ctrl+f", "f3", "ctrl+g"],
)
@pytest.mark.asyncio
async def test_read_only_disables_the_file_and_search_bindings(
    read_only_app: App, key: str
) -> None:
    async with read_only_app.run_test() as pilot:
        ta = read_only_app.query_one("#ta", expect_type=TextEditor)
        ta.text = ORIGINAL_TEXT
        await pilot.pause()

        await pilot.press(key)
        await pilot.pause()

        assert not ta.query(Input)
        assert ta.text_input is not None
        assert ta.text_input.has_focus


@pytest.mark.parametrize(
    "key",
    ["ctrl+s", "ctrl+o", "ctrl+f", "f3", "ctrl+g"],
)
@pytest.mark.asyncio
async def test_an_editable_editor_keeps_the_file_and_search_bindings(
    app: App, key: str
) -> None:
    async with app.run_test() as pilot:
        ta = app.query_one("#ta", expect_type=TextEditor)
        ta.text = ORIGINAL_TEXT
        await pilot.pause()

        await pilot.press(key)
        await pilot.pause()

        assert ta.query(Input)


class EscapeApp(App, inherit_bindings=False):
    """An app that binds escape, like a screen that shows a dismissable preview."""

    BINDINGS = [Binding("escape", "record_escape", "escape")]

    def __init__(self, read_only: bool) -> None:
        self.read_only = read_only
        self.escapes = 0
        super().__init__()

    def compose(self) -> ComposeResult:
        self.editor = TextEditor(language="python", read_only=self.read_only, id="ta")
        yield self.editor

    def on_mount(self) -> None:
        self.editor.focus()

    def action_record_escape(self) -> None:
        self.escapes += 1


@pytest.mark.asyncio
async def test_escape_bubbles_from_a_read_only_editor() -> None:
    """
    A read-only preview has no completion list to hide, so escape should reach
    a screen (or app) that binds it, without needing a priority binding.
    """
    app = EscapeApp(read_only=True)
    async with app.run_test() as pilot:
        ta = app.query_one("#ta", expect_type=TextEditor)
        ta.text = ORIGINAL_TEXT
        ta.selection = Selection(start=(0, 0), end=(0, 6))
        await pilot.pause()

        await pilot.press("escape")
        await pilot.pause()

        assert app.escapes == 1
        # the editor leaves the selection alone, too
        assert ta.selection == Selection(start=(0, 0), end=(0, 6))


@pytest.mark.asyncio
async def test_escape_does_not_bubble_from_an_editable_editor() -> None:
    app = EscapeApp(read_only=False)
    async with app.run_test() as pilot:
        ta = app.query_one("#ta", expect_type=TextEditor)
        ta.text = ORIGINAL_TEXT
        ta.selection = Selection(start=(0, 0), end=(0, 6))
        await pilot.pause()

        await pilot.press("escape")
        await pilot.pause()

        assert app.escapes == 0
        # instead, the editor collapses the selection
        assert ta.selection == Selection(start=(0, 6), end=(0, 6))
