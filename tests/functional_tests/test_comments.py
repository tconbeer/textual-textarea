import pytest
from textual.app import App
from textual.widgets.text_area import Selection
from textual_textarea import TextEditor


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
        ta = app.query_one("#ta", expect_type=TextEditor)
        ta.language = language
        original_text = "foo bar baz"
        ta.text = original_text
        ta.selection = Selection((0, 0), (0, 0))

        await pilot.press("ctrl+underscore")  # alias for ctrl+/
        assert ta.text == f"{expected_marker}{original_text}"

        await pilot.press("ctrl+underscore")  # alias for ctrl+/
        assert ta.text == f"{original_text}"
