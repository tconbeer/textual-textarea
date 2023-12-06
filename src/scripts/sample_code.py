from textual.app import App, ComposeResult
from textual_textarea import TextArea


class TextApp(App, inherit_bindings=False):
    def compose(self) -> ComposeResult:
        yield TextArea(
            language="python",
            theme="monokai",
            use_system_clipboard=True,
            id="ta",
        )

    def on_mount(self) -> None:
        ta = self.query_one("#ta", expect_type=TextArea)
        ta.focus()


if __name__ == "__main__":
    app = TextApp()
    app.run()
