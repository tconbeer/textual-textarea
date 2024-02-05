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
        self.editor.word_completer = lambda x: [
            (
                "supercalifragilisticexpialadociousASDFASDFASFASDF FX",
                "supercalifragilisticexpialadocious",
            )
        ]


app = TextApp()
app.run()
