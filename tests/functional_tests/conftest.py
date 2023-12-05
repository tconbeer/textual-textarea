from typing import Type, Union

import pytest
from textual.app import App, ComposeResult
from textual.driver import Driver
from textual.types import CSSPathType
from textual_textarea.next import TextArea as TextAreaNext
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
            language=self.language,
            use_system_clipboard=self.use_system_clipboard,
            id="ta",
        )

    def on_mount(self) -> None:
        ta = self.query_one("#ta")
        ta.focus()


class NextApp(App, inherit_bindings=False):
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
        yield TextAreaNext(language=self.language, id="ta")


@pytest.fixture(params=["TextArea", "next"])
def app(request: pytest.FixtureRequest) -> App:
    cls = TextAreaApp if request.param == "TextArea" else NextApp
    app = cls(language="python")
    return app


@pytest.fixture
def old_app(request: pytest.FixtureRequest) -> App:
    app = TextAreaApp(language="python")
    return app


@pytest.fixture
def next_app(request: pytest.FixtureRequest) -> App:
    app = NextApp(language="python")
    return app


@pytest.fixture(
    params=[("TextArea", False), ("next", False), ("TextArea", True), ("next", True)],
    ids=[
        "TA: no_sys_clipboard",
        "next: no_sys_clipboard",
        "TA: default",
        "next: default",
    ],
)
def app_all_clipboards(request: pytest.FixtureRequest) -> App:
    cls = TextAreaApp if request.param[0] == "TextArea" else NextApp
    app = cls(use_system_clipboard=request.param[1])
    return app
