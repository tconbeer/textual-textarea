from __future__ import annotations

from pathlib import Path
from typing import Callable

import pytest
from textual.app import App
from textual_textarea import TextArea
from textual_textarea.key_handlers import Cursor


@pytest.fixture
def word_completer() -> Callable[[str], list[tuple[str, str]]]:
    def _completer(prefix: str) -> list[tuple[str, str]]:
        words = [
            "satisfy",
            "season",
            "second",
            "seldom",
            "select",
            "self",
            "separate",
            "set",
            "space",
            "super",
        ]
        return [(w, w) for w in words if w.startswith(prefix)]

    return _completer


@pytest.mark.asyncio
async def test_autocomplete(
    app: App, word_completer: Callable[[str], list[tuple[str, str]]]
) -> None:
    async with app.run_test() as pilot:
        ta = app.query_one("#ta", expect_type=TextArea)
        ta.word_completer = word_completer
        ta.focus()

        await pilot.press("s")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert ta.text_input.completer_active == "word"
        assert ta.completion_list.open is True
        assert ta.completion_list.option_count == 10
        first_offset = ta.completion_list.styles.offset

        await pilot.press("e")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert ta.text_input.completer_active == "word"
        assert ta.completion_list.open is True
        assert ta.completion_list.option_count == 7
        assert ta.completion_list.styles.offset == first_offset

        await pilot.press("z")  # sez, no matches
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert ta.text_input.completer_active is None
        assert ta.completion_list.open is False

        # backspace when the list is not open doesn't re-open it
        await pilot.press("backspace")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert ta.text_input.completer_active is None
        assert ta.completion_list.open is False

        await pilot.press("l")  # sel
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert ta.text_input.completer_active == "word"
        assert ta.completion_list.open is True
        assert ta.completion_list.option_count == 3
        assert ta.completion_list.styles.offset == first_offset

        await pilot.press("backspace")  # se
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert ta.text_input.completer_active == "word"
        assert ta.completion_list.open is True
        assert ta.completion_list.option_count == 7
        assert ta.completion_list.styles.offset == first_offset

        await pilot.press("enter")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert ta.text_input.completer_active is None
        assert ta.completion_list.open is False
        assert ta.text == "season"
        assert ta.cursor.pos == 6


@pytest.mark.asyncio
async def test_autocomplete_paths(app: App, data_dir: Path) -> None:
    async with app.run_test() as pilot:
        ta = app.query_one("#ta", expect_type=TextArea)
        ta.focus()
        test_path = str(data_dir / "test_validator")
        ta.text = test_path
        ta.cursor = Cursor(lno=0, pos=len(test_path))

        await pilot.press("slash")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert ta.text_input.completer_active == "path"
        assert ta.completion_list.open is True
        assert ta.completion_list.option_count == 2
