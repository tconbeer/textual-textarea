from typing import Any, Union

from textual.containers import Container, ScrollableContainer
from textual.widget import Widget

from textual_textarea.colors import WidgetColors


class TextContainer(
    ScrollableContainer,
    inherit_bindings=False,
    can_focus=False,
    can_focus_children=True,
):
    DEFAULT_CSS = """
        TextContainer {
            height: 1fr;
            width: 100%
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
            width: 100%
        }
    """

    def __init__(
        self,
        theme_colors: WidgetColors,
        *children: Widget,
        name: Union[str, None] = None,
        id: Union[str, None] = None,
        classes: Union[str, None] = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(
            *children, name=name, id=id, classes=classes, disabled=disabled
        )
        self.theme_colors = theme_colors
