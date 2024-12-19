from __future__ import annotations

import sys

from textual.app import App, ComposeResult
from textual.widgets import Footer, Placeholder

from textual_textarea import TextEditor


class FocusablePlaceholder(Placeholder, can_focus=True):
    pass


class TextApp(App, inherit_bindings=False):
    BINDINGS = [("ctrl+q", "quit")]
    CSS = """
    TextEditor {
        height: 1fr;
    }
    Placeholder {
        height: 0fr;
    }
    """

    def compose(self) -> ComposeResult:
        try:
            language = sys.argv[1]
        except IndexError:
            language = "sql"
        yield FocusablePlaceholder()
        self.editor = TextEditor(
            language=language,
            use_system_clipboard=True,
            id="ta",
        )
        yield self.editor
        yield Footer()

    def watch_theme(self, theme: str) -> None:
        self.editor.theme = theme

    def on_mount(self) -> None:
        self.theme = "gruvbox"
        self.editor.focus()

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
                "supercalifragilisticexpialadocioussupercalifragilisticexpialadocious",
            ]
            return [((w, "word"), w) for w in words if w.startswith(prefix)]

        self.editor.word_completer = _completer


app = TextApp()
app.run()
