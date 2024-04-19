import pytest
from textual.app import App
from textual_textarea import TextEditor
from textual_textarea.goto_input import GotoLineInput


@pytest.mark.asyncio
async def test_goto_line(app: App) -> None:

    async with app.run_test() as pilot:
        ta = app.query_one("#ta", expect_type=TextEditor)
        ta.text = "\n" * 50
        await pilot.pause()
        assert ta.selection.start == ta.selection.end == (0, 0)
        await pilot.press("ctrl+g")

        goto_input = app.query_one(GotoLineInput)
        assert goto_input
        assert goto_input.has_focus
        assert "51" in goto_input.placeholder

        await pilot.press("1")
        await pilot.press("2")
        await pilot.press("enter")

        print(app.focused)
        assert ta.text_input.has_focus
        assert ta.selection.start == ta.selection.end == (11, 0)
