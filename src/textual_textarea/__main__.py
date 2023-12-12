import sys

from textual.app import App, ComposeResult
from textual.widgets import Placeholder

from textual_textarea import TextArea


class TextApp(App, inherit_bindings=False):
    CSS = """
    TextArea {
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
        yield Placeholder()
        yield TextArea(
            language=language,
            theme="nord-darker",
            use_system_clipboard=True,
            id="ta",
        )

    def on_mount(self) -> None:
        ta = self.query_one("#ta", expect_type=TextArea)
        ta.focus()


app = TextApp()
app.run()
