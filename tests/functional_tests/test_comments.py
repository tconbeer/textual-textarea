import pytest
from textual.app import App
from textual_textarea import TextArea
from textual_textarea.key_handlers import Cursor
from textual_textarea.next import TextArea as TextAreaNext


@pytest.mark.parametrize(
    "language,expected_marker",
    [
        ("python", "# "),
        ("sql", "-- "),
        # ("mysql", "# "),
        # ("c", "// "),
    ],
)
@pytest.mark.asyncio
async def test_comments(app: App, language: str, expected_marker: str) -> None:
    async with app.run_test() as pilot:
        ta = app.query_one("#ta")
        assert isinstance(ta, (TextArea, TextAreaNext))
        ta.language = language
        original_text = "foo bar baz"
        ta.text = original_text
        ta.cursor = Cursor(0, 0)

        await pilot.press("ctrl+underscore")  # alias for ctrl+/
        assert ta.text == f"{expected_marker}{original_text}"
