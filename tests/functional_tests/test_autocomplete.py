from __future__ import annotations

from pathlib import Path
from time import monotonic
from typing import Callable
from unittest.mock import MagicMock

import pytest
from textual.app import App
from textual.message import Message
from textual.widgets.text_area import Selection
from textual_textarea import TextEditor


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


@pytest.fixture
def word_completer_with_types() -> Callable[[str], list[tuple[tuple[str, str], str]]]:
    def _completer(prefix: str) -> list[tuple[tuple[str, str], str]]:
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
        return [((w, "word"), w) for w in words if w.startswith(prefix)]

    return _completer


@pytest.fixture
def member_completer() -> Callable[[str], list[tuple[str, str]]]:
    mock = MagicMock()
    mock.return_value = [("completion", "completion")]
    return mock


@pytest.mark.asyncio
async def test_autocomplete(
    app: App, word_completer: Callable[[str], list[tuple[str, str]]]
) -> None:
    messages: list[Message] = []
    async with app.run_test(message_hook=messages.append) as pilot:
        ta = app.query_one("#ta", expect_type=TextEditor)
        ta.word_completer = word_completer
        ta.focus()
        while ta.word_completer is None:
            await pilot.pause()

        start_time = monotonic()
        await pilot.press("s")
        while ta.completion_list.is_open is False:
            if monotonic() - start_time > 10:
                print("MESSAGES:")
                print("\n".join([str(m) for m in messages]))
                break
            await pilot.pause()
        assert ta.text_input
        assert ta.text_input.completer_active == "word"
        assert ta.completion_list.is_open is True
        assert ta.completion_list.option_count == 10
        first_offset = ta.completion_list.styles.offset

        await pilot.press("e")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert ta.text_input.completer_active == "word"
        assert ta.completion_list.is_open is True
        assert ta.completion_list.option_count == 7
        assert ta.completion_list.styles.offset == first_offset

        await pilot.press("z")  # sez, no matches
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert ta.text_input.completer_active is None
        assert ta.completion_list.is_open is False

        # backspace when the list is not open doesn't re-open it
        await pilot.press("backspace")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert ta.text_input.completer_active is None
        assert ta.completion_list.is_open is False

        await pilot.press("l")  # sel
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert ta.text_input.completer_active == "word"
        assert ta.completion_list.is_open is True
        assert ta.completion_list.option_count == 3
        assert ta.completion_list.styles.offset == first_offset

        await pilot.press("backspace")  # se
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert ta.text_input.completer_active == "word"
        assert ta.completion_list.is_open is True
        assert ta.completion_list.option_count == 7
        assert ta.completion_list.styles.offset == first_offset

        await pilot.press("enter")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert ta.text_input.completer_active is None
        assert ta.completion_list.is_open is False
        assert ta.text == "season"
        assert ta.selection.end[1] == 6


@pytest.mark.asyncio
async def test_autocomplete_with_types(
    app: App,
    word_completer_with_types: Callable[[str], list[tuple[tuple[str, str], str]]],
) -> None:
    messages: list[Message] = []
    word_completer = word_completer_with_types
    async with app.run_test(message_hook=messages.append) as pilot:
        ta = app.query_one("#ta", expect_type=TextEditor)
        ta.word_completer = word_completer
        ta.focus()
        while ta.word_completer is None:
            await pilot.pause()

        start_time = monotonic()
        await pilot.press("s")
        while ta.completion_list.is_open is False:
            if monotonic() - start_time > 10:
                print("MESSAGES:")
                print("\n".join([str(m) for m in messages]))
                break
            await pilot.pause()
        assert ta.text_input
        assert ta.text_input.completer_active == "word"
        assert ta.completion_list.is_open is True
        assert ta.completion_list.option_count == 10
        first_offset = ta.completion_list.styles.offset

        await pilot.press("e")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert ta.text_input.completer_active == "word"
        assert ta.completion_list.is_open is True
        assert ta.completion_list.option_count == 7
        assert ta.completion_list.styles.offset == first_offset

        await pilot.press("z")  # sez, no matches
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert ta.text_input.completer_active is None
        assert ta.completion_list.is_open is False

        # backspace when the list is not open doesn't re-open it
        await pilot.press("backspace")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert ta.text_input.completer_active is None
        assert ta.completion_list.is_open is False

        await pilot.press("l")  # sel
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert ta.text_input.completer_active == "word"
        assert ta.completion_list.is_open is True
        assert ta.completion_list.option_count == 3
        assert ta.completion_list.styles.offset == first_offset

        await pilot.press("backspace")  # se
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert ta.text_input.completer_active == "word"
        assert ta.completion_list.is_open is True
        assert ta.completion_list.option_count == 7
        assert ta.completion_list.styles.offset == first_offset

        await pilot.press("enter")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert ta.text_input.completer_active is None
        assert ta.completion_list.is_open is False
        assert ta.text == "season"
        assert ta.selection.end[1] == 6


@pytest.mark.asyncio
async def test_autocomplete_paths(app: App, data_dir: Path) -> None:
    messages: list[Message] = []
    async with app.run_test(message_hook=messages.append) as pilot:
        ta = app.query_one("#ta", expect_type=TextEditor)
        ta.focus()
        test_path = str(data_dir / "test_validator")
        ta.text = test_path
        await pilot.pause()
        ta.selection = Selection((0, len(test_path)), (0, len(test_path)))

        start_time = monotonic()
        await pilot.press("slash")
        while ta.completion_list.is_open is False:
            if monotonic() - start_time > 10:
                print("MESSAGES:")
                print("\n".join([str(m) for m in messages]))
                break
            await pilot.pause()
        assert ta.text_input
        assert ta.text_input.completer_active == "path"
        assert ta.completion_list.is_open is True
        assert ta.completion_list.option_count == 2


@pytest.mark.parametrize(
    "text,keys,expected_prefix",
    [
        ("foo bar", ["full_stop"], "bar."),
        ("foo 'bar'", ["full_stop"], "'bar'."),
        ("foo `bar`", ["full_stop"], "`bar`."),
        ('foo "bar"', ["full_stop"], '"bar".'),
        ("foo bar", ["colon"], "bar:"),
        ("foo bar", ["colon", "colon"], "bar::"),
        ('foo "bar"', ["colon", "colon"], '"bar"::'),
        ("foo bar", ["full_stop", "quotation_mark"], 'bar."'),
        ('foo "bar"', ["full_stop", "quotation_mark"], '"bar"."'),
    ],
)
@pytest.mark.asyncio
async def test_autocomplete_members(
    app: App,
    member_completer: MagicMock,
    text: str,
    keys: list[str],
    expected_prefix: str,
) -> None:
    messages: list[Message] = []
    async with app.run_test(message_hook=messages.append) as pilot:
        ta = app.query_one("#ta", expect_type=TextEditor)
        ta.member_completer = member_completer
        ta.focus()
        while ta.member_completer is None:
            await pilot.pause()
        ta.text = text
        ta.selection = Selection((0, len(text)), (0, len(text)))
        await pilot.pause()
        for key in keys:
            await pilot.press(key)

        start_time = monotonic()
        while ta.completion_list.is_open is False:
            if monotonic() - start_time > 10:
                print("MESSAGES:")
                print("\n".join([str(m) for m in messages]))
                break
            await pilot.pause()

        member_completer.assert_called_with(expected_prefix)
        assert ta.text_input is not None
        assert ta.text_input.completer_active == "member"
        assert ta.completion_list.is_open is True
