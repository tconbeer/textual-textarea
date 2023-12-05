import sys

from textual.app import App, ComposeResult

from textual_textarea import TextArea
from textual_textarea.next import TextArea as TextAreaNext


class TextApp(App, inherit_bindings=False):
    def compose(self) -> ComposeResult:
        try:
            language = sys.argv[1]
        except IndexError:
            language = "python"
        yield TextArea(
            language=language, theme="zenburn", use_system_clipboard=True, id="ta"
        )

    def on_mount(self) -> None:
        ta = self.query_one("#ta")
        ta.focus()


class NextApp(App, inherit_bindings=False):
    def compose(self) -> ComposeResult:
        try:
            language = sys.argv[1]
        except IndexError:
            language = "python"
        yield TextAreaNext(
            language=language, theme="monokai", use_system_clipboard=True, id="ta"
        )

    def on_mount(self) -> None:
        ta = self.query_one("#ta")
        ta.focus()


app = NextApp()
# app = TextApp()
app.run()
