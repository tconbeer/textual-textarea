from pathlib import Path
from typing import List

import pytest
from textual.app import App
from textual.message import Message
from textual.widgets import Input
from textual_textarea import TextArea, TextAreaSaved


@pytest.mark.parametrize("filename", ["foo.py", "empty.py"])
@pytest.mark.asyncio
async def test_open(data_dir: Path, app: App, filename: str) -> None:
    p = data_dir / "test_open" / filename
    with open(p, "r") as f:
        contents = f.read()

    async with app.run_test() as pilot:
        ta = app.query_one("#ta", expect_type=TextArea)
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


@pytest.mark.asyncio
async def test_save(app: App, tmp_path: Path) -> None:
    TEXT = "select\n    1 as a,\n    2 as b,\n    'c' as c"
    p = tmp_path / "text.sql"
    print(p)
    messages: List[Message] = []
    async with app.run_test(message_hook=messages.append) as pilot:
        ta = app.query_one("#ta", expect_type=TextArea)
        ta.text = TEXT

        await pilot.press("ctrl+s")
        save_input = ta.query_one(Input)
        assert save_input.id and "save" in save_input.id
        assert save_input.has_focus

        save_input.value = str(p)
        await pilot.press("enter")
        await pilot.pause()
        assert len(messages) > 1
        assert Input.Submitted in [msg.__class__ for msg in messages]
        assert TextAreaSaved in [msg.__class__ for msg in messages]

        with open(p, "r") as f:
            saved_text = f.read()
        assert saved_text == TEXT
