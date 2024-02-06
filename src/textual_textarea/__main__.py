from __future__ import annotations

import sys

from textual.app import App, ComposeResult
from textual.widgets import Placeholder

from textual_textarea import TextEditor


class FocusablePlaceholder(Placeholder, can_focus=True):
    pass


class TextApp(App, inherit_bindings=False):
    CSS = """
    TextEditor {
        height: 1fr;
    }
    Placeholder {
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        try:
            language = sys.argv[1]
        except IndexError:
            language = "python"
        yield FocusablePlaceholder()
        self.editor = TextEditor(
            language=language,
            theme="nord-darker",
            use_system_clipboard=True,
            id="ta",
        )
        yield self.editor

    def on_mount(self) -> None:
        self.editor.focus()

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
                "supercalifragilisticexpialadocioussupercalifragilisticexpialadocious",
            ]
            return [(w, w) for w in words if w.startswith(prefix)]

        self.editor.word_completer = _completer


app = TextApp()
app.run()
