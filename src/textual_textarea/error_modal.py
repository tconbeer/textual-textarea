from typing import Union

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static


class ErrorModal(ModalScreen):
    DEFAULT_CSS = """
        ErrorModal {
            align: center middle;
            padding: 0;
        }
        #error_modal__outer {
            border: round $error;
            background: $background;
            margin: 5 10;
            padding: 1 2;
            max-width: 88;
        }

        #error_modal__header {
            dock: top;
            color: $text-muted;
            margin: 0 0 1 0;
            padding: 0 1;
        }

        #error_modal__inner {
            border: round $background;
            padding: 1 1 1 2;
        }

        #error_modal__info {
            padding: 0 3 0 0;
        }

        #error_modal__footer {
            dock: bottom;
            color: $text-muted;
            margin: 1 0 0 0;
            padding: 0 1;
        }
    """

    def __init__(
        self,
        title: str,
        header: str,
        error: BaseException,
        name: Union[str, None] = None,
        id: Union[str, None] = None,
        classes: Union[str, None] = None,
    ) -> None:
        self.title = title
        self.header = header
        self.error = error
        super().__init__(name, id, classes)

    def compose(self) -> ComposeResult:
        with Vertical(id="error_modal__outer"):
            yield Static(self.header, id="error_modal__header")
            with Vertical(id="error_modal__inner"):
                with VerticalScroll():
                    yield Static(str(self.error), id="error_modal__info")
            yield Static("Press any key to continue.", id="error_modal__footer")

    def on_mount(self) -> None:
        container = self.query_one("#error_modal__outer")
        container.border_title = self.title

    def on_key(self) -> None:
        self.app.pop_screen()
        self.app.action_focus_next()
