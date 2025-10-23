from typing import Any, Union

from textual import on
from textual.containers import Container, ScrollableContainer
from textual.events import Click
from textual.widget import Widget


class TextContainer(
    ScrollableContainer,
    inherit_bindings=False,
    can_focus=False,
    can_focus_children=True,
):
    DEFAULT_CSS = """
        TextContainer {
            height: 1fr;
            width: 100%;
            layers: main overlay;
        }
    """

    def scroll_to(
        self, x: Union[float, None] = None, y: Union[float, None] = None, **_: Any
    ) -> None:
        return super().scroll_to(x, y, animate=True, duration=0.01)


class FooterContainer(
    Container,
    inherit_bindings=False,
    can_focus=False,
    can_focus_children=True,
):
    DEFAULT_CSS = """
        FooterContainer {
            dock: bottom;
            height: auto;
            width: 100%;
        }
        FooterContainer.hide {
            height: 0;
        }
    """

    def __init__(
        self,
        *children: Widget,
        name: Union[str, None] = None,
        id: Union[str, None] = None,  # noqa: A002
        classes: Union[str, None] = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(
            *children, name=name, id=id, classes=classes, disabled=disabled
        )

    @on(Click)
    def handle_click(self, event: Click) -> None:
        """
        Prevent clicks on inputs in the footer container from
        bubbling up to the TextArea widget, which casuses
        a race condition for the app focus.
        """
        event.stop()
