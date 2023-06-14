import sys

from textual.app import App, ComposeResult

from textual_textarea import TextArea


class TextApp(App, inherit_bindings=False):
    def compose(self) -> ComposeResult:
        try:
            language = sys.argv[1]
        except IndexError:
            language = "python"
        yield TextArea(language=language, theme="monokai", use_system_clipboard=True)

    def on_mount(self) -> None:
        ta = self.query_one(TextArea)
        ta.focus()


app = TextApp()
app.run()
