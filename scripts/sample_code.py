from textual.app import App, ComposeResult

from textual_textarea import TextEditor


class TextApp(App, inherit_bindings=False):
    def compose(self) -> ComposeResult:
        self.editor = TextEditor(
            language="python",
            theme="monokai",
            use_system_clipboard=True,
        )
        yield self.editor

    def on_mount(self) -> None:
        self.editor.focus()


if __name__ == "__main__":
    app = TextApp()
    app.run()
