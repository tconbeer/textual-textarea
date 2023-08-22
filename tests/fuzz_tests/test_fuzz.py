from typing import List

import pytest
from hypothesis import Verbosity, given, settings
from hypothesis.strategies import lists, sampled_from, text
from textual.app import App, ComposeResult
from textual_textarea import TextArea
from textual_textarea.serde import deserialize_lines, serialize_lines


class TextAreaApp(App, inherit_bindings=False):
    def compose(self) -> ComposeResult:
        yield TextArea(language=None, use_system_clipboard=False)

    def on_mount(self) -> None:
        self.text_area = self.query_one(TextArea)
        self.text_area.focus()


KEYS = [
    "up",
    "down",
    "left",
    "right",
    "ctrl+right",
    "ctrl+left",
    "home",
    "end",
    "backspace",
    "delete",
    "shift+up",
    "shift+down",
    "shift+left",
    "shift+right",
    "a",
    "b",
    "c",
    "d",
    "e",
    "f",
    "g",
    "enter",
    "ctrl+underscore",
    "shift+delete",
    "ctrl+a",
]


@given(keys=lists(sampled_from(KEYS), min_size=5, max_size=10))
@settings(deadline=1000, max_examples=10, verbosity=Verbosity.verbose)
@pytest.mark.asyncio
async def test_fuzz_keys(keys: List[str]) -> None:
    print("--New test--")
    app = TextAreaApp()
    async with app.run_test() as pilot:
        ta = app.query_one(TextArea)
        ta.text = "foo\nbar\nbaz\n\n\n"
        ta.text_input.clipboard = ["clipped!"]
        for key in keys:
            await pilot.press(key)
    app.exit()


@given(s=text())
def test_fuzz_serde(s: str) -> None:
    lines = deserialize_lines(s)
    serialize_lines(lines)
