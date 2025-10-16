from textual.app import App, ComposeResult

from textual_textarea import TextEditor


class TextApp(App, inherit_bindings=False):
    def compose(self) -> ComposeResult:
        self.ta = TextEditor(
            text="class TextApp(App):",
            language="python",
            theme="monokai",
            use_system_clipboard=True,
            id="ta",
        )
        yield self.ta

    def on_mount(self) -> None:
        self.ta.focus()
        self.exit()


if __name__ == "__main__":
    app = TextApp()
    app.run()
