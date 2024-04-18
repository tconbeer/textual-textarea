from typing import Type, Union
from unittest.mock import MagicMock

import pytest
from textual.app import App, ComposeResult
from textual.driver import Driver
from textual.types import CSSPathType
from textual_textarea.text_editor import TextEditor


class TextEditorApp(App, inherit_bindings=False):
    def __init__(
        self,
        driver_class: Union[Type[Driver], None] = None,
        css_path: Union[CSSPathType, None] = None,
        watch_css: bool = False,
        language: Union[str, None] = None,
        use_system_clipboard: bool = True,
    ):
        self.language = language
        self.use_system_clipboard = use_system_clipboard
        super().__init__(driver_class, css_path, watch_css)

    def compose(self) -> ComposeResult:
        self.editor = TextEditor(
            language=self.language,
            use_system_clipboard=self.use_system_clipboard,
            id="ta",
        )
        yield self.editor

    def on_mount(self) -> None:
        self.editor.focus()


@pytest.fixture
def app() -> App:
    app = TextEditorApp(language="python")
    return app


@pytest.fixture(
    params=[False, True],
    ids=["no_sys_clipboard", "default"],
)
def app_all_clipboards(request: pytest.FixtureRequest) -> App:
    app = TextEditorApp(use_system_clipboard=request.param)
    return app


@pytest.fixture(autouse=True)
def mock_pyperclip(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = MagicMock()
    mock.determine_clipboard.return_value = mock.copy, mock.paste

    def set_paste(x: str) -> None:
        mock.paste.return_value = x

    mock.copy.side_effect = set_paste
    monkeypatch.setattr("textual_textarea.text_editor.pyperclip", mock)

    return mock
