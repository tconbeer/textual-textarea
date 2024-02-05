import asyncio
from pathlib import Path

from textual.app import App, ComposeResult
from textual_textarea import TextEditor

contents = (Path(__file__).parent / "sample_code.py").open("r").read()


class TextApp(App, inherit_bindings=False):
    def compose(self) -> ComposeResult:
        self.editor = TextEditor(
            language="python",
            theme="monokai",
            use_system_clipboard=True,
            id="ta",
        )
        yield self.editor

    def on_mount(self) -> None:
        self.editor.focus()


async def take_screenshot() -> None:
    app = TextApp()
    async with app.run_test(size=(80, 24)):
        app.editor.text = contents
        app.editor.cursor = (8, 12)  # type: ignore
        app.editor.selection_anchor = (7, 12)  # type: ignore
        app.save_screenshot("textarea.svg")


asyncio.run(take_screenshot())
