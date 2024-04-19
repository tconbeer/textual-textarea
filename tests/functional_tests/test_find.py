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


@pytest.mark.asyncio
async def test_find_history(app: App) -> None:

    async with app.run_test() as pilot:
        ta = app.query_one("#ta", expect_type=TextEditor)
        ta.text = "foo bar\n" * 50
        await pilot.pause()

        # add an item to the history by pressing enter
        await pilot.press("ctrl+f")
        await pilot.press("a")
        await pilot.press("enter")
        await pilot.press("escape")

        # re-open the find input and navigate the one-item
        # history
        await pilot.press("ctrl+f")
        find_input = app.query_one(FindInput)
        assert find_input.value == ""
        await pilot.press("up")
        assert find_input.value == "a"
        await pilot.press("down")
        assert find_input.value == ""
        await pilot.press("up")
        await pilot.press("up")
        assert find_input.value == "a"
        await pilot.press("down")
        assert find_input.value == ""

        # add an item to the history by closing the find input
        await pilot.press("b")
        await pilot.press("escape")

        # navigate the two-item history
        await pilot.press("ctrl+f")
        find_input = app.query_one(FindInput)
        assert find_input.value == ""
        await pilot.press("up")
        assert find_input.value == "b"
        await pilot.press("down")
        assert find_input.value == ""
        await pilot.press("up")
        assert find_input.value == "b"
        await pilot.press("up")
        assert find_input.value == "a"
        await pilot.press("up")
        assert find_input.value == "a"
        await pilot.press("down")
        assert find_input.value == "b"
        await pilot.press("down")
        assert find_input.value == ""
