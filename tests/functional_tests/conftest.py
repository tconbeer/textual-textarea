from typing import Type, Union

import pytest
from textual.app import App, ComposeResult
from textual.driver import Driver
from textual.types import CSSPathType
from textual_textarea.textarea import TextArea


class TextAreaApp(App, inherit_bindings=False):
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
        yield TextArea(
            language=self.language, use_system_clipboard=self.use_system_clipboard
        )

    def on_mount(self) -> None:
        ta = self.query_one(TextArea)
        ta.focus()


@pytest.fixture
def app() -> App:
    app = TextAreaApp(language="python")
    return app


@pytest.fixture(params=[False, True], ids=["no_sys_clipboard", "default"])
def app_all_clipboards(request: pytest.FixtureRequest) -> App:
    app = TextAreaApp(use_system_clipboard=request.param)
    return app
