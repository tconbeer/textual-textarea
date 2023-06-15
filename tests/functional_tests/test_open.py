from pathlib import Path

import pytest
from textual.app import App
from textual.widgets import Input
from textual_textarea import TextArea


@pytest.mark.parametrize("filename", ["foo.py", "empty.py"])
@pytest.mark.asyncio
async def test_open(data_dir: Path, app: App, filename: str) -> None:
    p = data_dir / "test_open" / filename
    with open(p, "r") as f:
        contents = f.read()

    async with app.run_test() as pilot:
        ta = app.query_one(TextArea)
        assert ta.text == ""
        starting_text = "123"
        for key in starting_text:
            await pilot.press(key)
        assert ta.text == starting_text

        await pilot.press("ctrl+o")
        open_input = ta.query_one(Input)
        assert open_input.id and "open" in open_input.id
        assert open_input.has_focus

        for key in str(p):
            await pilot.press(key)
        await pilot.press("enter")

        assert ta.text == contents
        assert ta.text_input.has_focus

        # make sure the end of the buffer is formatted properly.
        # these previously caused a crash.
        await pilot.press("ctrl+end")
        assert ta.cursor.pos >= 0
        await pilot.press("enter")
