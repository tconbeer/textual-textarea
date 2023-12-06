import asyncio
from pathlib import Path

from textual.app import App, ComposeResult
from textual_textarea import TextArea

contents = (Path(__file__).parent / "sample_code.py").open("r").read()


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


async def take_screenshot() -> None:
    app = TextApp()
    async with app.run_test(size=(80, 24)):
        ta = app.query_one("#ta", expect_type=TextArea)
        ta.text = contents
        ta.cursor = (8, 12)  # type: ignore
        ta.selection_anchor = (7, 12)  # type: ignore
        app.save_screenshot("textarea.svg")


asyncio.run(take_screenshot())
