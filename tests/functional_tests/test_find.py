import pytest
from textual.app import App
from textual_textarea import TextEditor
from textual_textarea.find_input import FindInput


@pytest.mark.asyncio
async def test_find(app: App) -> None:

    async with app.run_test() as pilot:
        ta = app.query_one("#ta", expect_type=TextEditor)
        ta.text = "foo bar\n" * 50
        await pilot.pause()
        assert ta.selection.start == ta.selection.end == (0, 0)
        await pilot.press("ctrl+f")

        find_input = app.query_one(FindInput)
        assert find_input
        assert find_input.has_focus
        assert "Find" in find_input.placeholder

        await pilot.press("b")
        assert find_input.has_focus
        assert ta.selection.start == (0, 4)
        assert ta.selection.end == (0, 5)

        await pilot.press("a")
        assert find_input.has_focus
        assert ta.selection.start == (0, 4)
        assert ta.selection.end == (0, 6)

        await pilot.press("enter")
        assert find_input.has_focus
        assert ta.selection.start == (1, 4)
        assert ta.selection.end == (1, 6)

        await pilot.press("escape")
        assert ta.text_input.has_focus
        assert ta.selection.start == (1, 4)
        assert ta.selection.end == (1, 6)

        await pilot.press("ctrl+f")

        find_input = app.query_one(FindInput)
        await pilot.press("f")
        assert find_input.has_focus
        assert ta.selection.start == (2, 0)
        assert ta.selection.end == (2, 1)
