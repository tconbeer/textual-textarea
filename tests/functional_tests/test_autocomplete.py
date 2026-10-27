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
async def test_focus_does_not_dismiss_completion_list(
    app: App, word_completer: Callable[[str], list[tuple[str, str]]]
) -> None:
    """
    Focusing the TextEditor when it already holds focus must not blur the inner
    TextArea, since the blur dismisses an open completion list.
    """
    async with app.run_test() as pilot:
        ta = app.query_one("#ta", expect_type=TextEditor)
        ta.word_completer = word_completer
        assert ta.text_input is not None

        await pilot.press("s")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert ta.completion_list.is_open is True

        ta.focus()
        await pilot.pause()
        assert ta.text_input.has_focus is True
        assert ta.text_input.completer_active == "word"
        assert ta.completion_list.is_open is True


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


@pytest.mark.asyncio
async def test_accepting_completion_scrolls_cursor_into_view(app: App) -> None:
    """
    Accepting a completion wider than the viewport leaves the cursor on screen.

    Same Textual 7.x behavior change as test_paste_scrolls_cursor_into_view:
    replace() no longer scrolls the cursor into view on its own.
    """
    long_word = "s" + "u" * 150

    def completer(prefix: str) -> list[tuple[str, str]]:
        return [(long_word, long_word)]

    async with app.run_test(size=(80, 24)) as pilot:
        ta = app.query_one("#ta", expect_type=TextEditor)
        ta.word_completer = completer
        ta.focus()
        while ta.word_completer is None:
            await pilot.pause()
        assert ta.text_input is not None

        # start at the right edge of the viewport, but still on screen
        prefix = "-" * 70
        ta.text = prefix
        ta.selection = Selection((0, len(prefix)), (0, len(prefix)))
        await pilot.pause()
        assert ta.text_input.scroll_offset.x == 0

        start_time = monotonic()
        await pilot.press("s")
        while ta.completion_list.is_open is False:
            if monotonic() - start_time > 10:
                break
            await pilot.pause()
        assert ta.completion_list.is_open is True

        await pilot.press("enter")
        await app.workers.wait_for_complete()
        await pilot.pause()

        assert ta.text == prefix + long_word
        assert ta.selection.end[1] == len(prefix) + len(long_word)
        assert ta.text_input.scroll_offset.x > 0


@pytest.mark.parametrize(
    "text,keys,value,expected_prefix,expected_text,expected_cursor_column",
    [
        ("", ["m", "y"], "myfunc", "my", "myfunc", 6),
        ("", ["m", "y"], '"myfunc"', "my", '"myfunc"', 8),
        # the quote and the one the editor auto-closed stay around a bare value
        ("", ["quotation_mark", "m", "y"], "myfunc", "my", '"myfunc"', 7),
        # a quoted value replaces both
        ("", ["quotation_mark", "m", "y"], '"myfunc"', "my", '"myfunc"', 8),
        # a value that opens the quote but doesn't close it keeps the closing one
        ("", ["quotation_mark", "m", "y"], '"myfunc', "my", '"myfunc"', 7),
        ("", ["apostrophe", "m", "y"], "'myfunc'", "my", "'myfunc'", 8),
        # backticks aren't auto-closed
        ("", ["grave_accent", "m", "y"], "`myfunc`", "my", "`myfunc`", 8),
        ("", ["quotation_mark", "m", "y", "backspace"], '"myfunc"', "m", '"myfunc"', 8),
        # a quote after a word character or another quote doesn't open the word
        ('"foo"', ["b", "a"], '"bar"', "ba", '"foo""bar"', 10),
        ('"a""', ["b"], '"b"', "b", '"a"""b"', 7),
        ("x'", ["a"], "'ab'", "a", "x''ab'", 6),
    ],
)
@pytest.mark.asyncio
async def test_accepting_quoted_word_completion(
    app: App,
    text: str,
    keys: list[str],
    value: str,
    expected_prefix: str,
    expected_text: str,
    expected_cursor_column: int,
) -> None:
    completer = MagicMock(return_value=[(value, value)])
    async with app.run_test() as pilot:
        ta = app.query_one("#ta", expect_type=TextEditor)
        ta.word_completer = completer
        ta.focus()
        while ta.word_completer is None:
            await pilot.pause()
        ta.text = text
        ta.selection = Selection((0, len(text)), (0, len(text)))
        await pilot.pause()
        for key in keys:
            await pilot.press(key)

        start_time = monotonic()
        while ta.completion_list.is_open is False:
            if monotonic() - start_time > 10:
                break
            await pilot.pause()
        completer.assert_called_with(expected_prefix)
        assert ta.completion_list.is_open is True

        await pilot.press("enter")
        await app.workers.wait_for_complete()
        await pilot.pause()

        assert ta.text == expected_text
        assert ta.selection.end == (0, expected_cursor_column)


@pytest.mark.asyncio
async def test_word_completion_after_backspacing_over_the_quote(app: App) -> None:
    """
    With its opening quote deleted, a word has no quote to replace, so the quote
    the editor auto-closed is left alone.
    """
    completer = MagicMock(return_value=[('"myfunc"', '"myfunc"')])
    async with app.run_test() as pilot:
        ta = app.query_one("#ta", expect_type=TextEditor)
        ta.word_completer = completer
        ta.focus()
        while ta.word_completer is None:
            await pilot.pause()
        for key in ["quotation_mark", "m", "backspace", "backspace", "m", "y"]:
            await pilot.press(key)
        assert ta.text == 'my"'

        start_time = monotonic()
        while ta.completion_list.is_open is False:
            if monotonic() - start_time > 10:
                break
            await pilot.pause()
        completer.assert_called_with("my")

        await pilot.press("enter")
        await app.workers.wait_for_complete()
        await pilot.pause()

        assert ta.text == '"myfunc""'
        assert ta.selection.end == (0, 8)


@pytest.mark.asyncio
async def test_accepting_quoted_word_completion_without_closing_quote(
    app: App,
) -> None:
    """
    A quote typed before a word character isn't auto-closed, so there is no
    closing quote after the cursor to replace.
    """
    completer = MagicMock(return_value=[('"myfunc"', '"myfunc"')])
    async with app.run_test() as pilot:
        ta = app.query_one("#ta", expect_type=TextEditor)
        ta.word_completer = completer
        ta.focus()
        while ta.word_completer is None:
            await pilot.pause()
        ta.text = "rest"
        ta.selection = Selection((0, 0), (0, 0))
        await pilot.pause()
        for key in ["quotation_mark", "m", "y"]:
            await pilot.press(key)
        assert ta.text == '"myrest'

        start_time = monotonic()
        while ta.completion_list.is_open is False:
            if monotonic() - start_time > 10:
                break
            await pilot.pause()
        completer.assert_called_with("my")

        await pilot.press("enter")
        await app.workers.wait_for_complete()
        await pilot.pause()

        assert ta.text == '"myfunc"rest'
        assert ta.selection.end == (0, 8)


@pytest.mark.parametrize(
    "value,expected_text,expected_cursor_column",
    [
        # the value closes the quote, so it replaces the auto-closed one
        ('public."myfunc"', 'public."myfunc"', 15),
        # the auto-closed quote closes a value that leaves it open
        ('public."myfunc', 'public."myfunc"', 14),
    ],
)
@pytest.mark.asyncio
async def test_accepting_quoted_member_completion(
    app: App, value: str, expected_text: str, expected_cursor_column: int
) -> None:
    completer = MagicMock(return_value=[(value, value)])
    async with app.run_test() as pilot:
        ta = app.query_one("#ta", expect_type=TextEditor)
        ta.member_completer = completer
        ta.focus()
        while ta.member_completer is None:
            await pilot.pause()
        ta.text = "public"
        ta.selection = Selection((0, 6), (0, 6))
        await pilot.pause()
        for key in ["full_stop", "quotation_mark", "m", "y"]:
            await pilot.press(key)

        start_time = monotonic()
        while ta.completion_list.is_open is False:
            if monotonic() - start_time > 10:
                break
            await pilot.pause()
        completer.assert_called_with('public."my')

        await pilot.press("enter")
        await app.workers.wait_for_complete()
        await pilot.pause()

        assert ta.text == expected_text
        assert ta.selection.end == (0, expected_cursor_column)
