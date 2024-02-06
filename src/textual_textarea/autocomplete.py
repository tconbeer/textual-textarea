from __future__ import annotations

from typing import Callable

from rich.console import RenderableType
from rich.text import Text
from textual import on, work
from textual.css.scalar import Scalar, ScalarOffset, Unit
from textual.events import Key, Resize
from textual.geometry import Size
from textual.message import Message
from textual.reactive import Reactive, reactive
from textual.widget import Widget
from textual.widgets import OptionList
from textual.widgets._option_list import NewOptionListContent
from textual.widgets.option_list import Option

from textual_textarea.messages import TextAreaHideCompletionList


class Completion(Option):
    def __init__(
        self,
        prompt: RenderableType,
        id: str | None = None,
        disabled: bool = False,
        value: str | None = None,
    ) -> None:
        super().__init__(prompt, id, disabled)
        self.value = value


class CompletionList(OptionList, can_focus=False, inherit_bindings=False):
    DEFAULT_CSS = """
    CompletionList {
        layer: overlay;
        padding: 0;
        border: none;
        width: 40;
        max-height: 8;
        display: none;
    }
    CompletionList.open {
        display: block;
    }
    """

    class CompletionsReady(Message, bubble=False):
        def __init__(self, prefix: str, items: list[tuple[str, str]]) -> None:
            super().__init__()
            self.items = items
            self.prefix = prefix

    INNER_CONTENT_WIDTH = 37  # should be 3 less than width for scroll bar.
    open: Reactive[bool] = reactive(False)
    cursor_offset: tuple[int, int] = (0, 0)
    additional_x_offset: int = 0

    def __init__(
        self,
        *content: NewOptionListContent,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ):
        super().__init__(
            *content, name=name, id=id, classes=classes, disabled=disabled, wrap=False
        )

    def set_offset(self, x_offset: int, y_offset: int) -> None:
        """The CSS Offset of this widget from its parent."""
        self.styles.offset = ScalarOffset.from_offset(
            (
                x_offset,
                y_offset,
            )
        )

    @property
    def x_offset(self) -> int:
        """The x-coord of the CSS Offset of this widget from its parent."""
        return int(self.styles.offset.x.value)

    @property
    def y_offset(self) -> int:
        """The y-coord of the CSS Offset of this widget from its parent."""
        return int(self.styles.offset.y.value)

    @property
    def parent_height(self) -> int:
        """
        The content size height of the parent widget
        """
        return self.parent_size.height

    @property
    def parent_width(self) -> int:
        """
        The content size height of the parent widget
        """
        return self.parent_size.width

    @property
    def parent_size(self) -> Size:
        """
        The content size of the parent widget
        """
        parent = self.parent
        if isinstance(parent, Widget):
            return parent.content_size
        else:
            return self.screen.content_size

    @on(CompletionsReady)
    def populate_and_position_list(self, event: CompletionsReady) -> None:
        event.stop()
        self.clear_options()

        # if the completions' prompts are wider than the widget,
        # we have to trunctate them
        prompts = [Text.from_markup(item[0]) for item in event.items]
        max_length = max(map(lambda x: x.cell_len, prompts))
        truncate_amount = max(
            0,
            min(
                max_length - self.INNER_CONTENT_WIDTH,
                len(event.prefix) - 2,
            ),
        )
        if truncate_amount > 0:
            additional_x_offset = truncate_amount - 1
            items = [
                Completion(prompt=f"…{prompt[truncate_amount:]}", value=item[1])
                for prompt, item in zip(prompts, event.items)
            ]
        else:
            additional_x_offset = 0
            items = [Completion(prompt=item[0], value=item[1]) for item in event.items]

        # set x offset if not already open.
        if not self.open:
            try:
                x_offset = self._get_x_offset(
                    prefix_length=len(event.prefix),
                    additional_x_offset=additional_x_offset,
                    cursor_x=self.cursor_offset[0],
                    container_width=self.parent_width,
                    width=self._width,
                )
            except ValueError:
                x_offset = 0
                self.styles.width = self._parent_container_size.width
            self.set_offset(x_offset, self.y_offset)
        # adjust x offset if we have to due to truncation
        elif additional_x_offset != self.additional_x_offset:
            self.set_offset(
                min(
                    self.x_offset + (additional_x_offset - self.additional_x_offset),
                    self.parent_width - self._width,
                ),
                self.y_offset,
            )

        self.add_options(items=items)
        self.action_first()
        self.additional_x_offset = additional_x_offset
        self.open = True

    def watch_open(self, open: bool) -> None:
        if not open:
            self.remove_class("open")
            self.additional_x_offset = 0
            return

        self.add_class("open")
        self.styles.max_height = Scalar(
            value=8.0, unit=Unit.CELLS, percent_unit=Unit.PERCENT
        )

    def on_resize(self, event: Resize) -> None:
        try:
            y_offset = self._get_y_offset(
                cursor_y=self.cursor_offset[1],
                height=event.size.height,
                container_height=self.parent_height,
            )
        except ValueError:
            if self.styles.max_height is not None and self.styles.max_height.value > 1:
                self.styles.max_height = Scalar(
                    value=self.styles.max_height.value - 1,
                    unit=self.styles.max_height.unit,
                    percent_unit=self.styles.max_height.percent_unit,
                )
            else:
                self.post_message(TextAreaHideCompletionList())
        else:
            self.set_offset(self.x_offset, y_offset)

    @work(thread=True, exclusive=True, group="completers")
    def show_completions(
        self,
        prefix: str,
        completer: Callable[[str], list[tuple[str, str]]] | None,
    ) -> None:
        matches = completer(prefix) if completer is not None else []
        if matches:
            self.post_message(self.CompletionsReady(prefix=prefix, items=matches))
        else:
            self.post_message(TextAreaHideCompletionList())

    def process_keypress(self, event: Key) -> None:
        if event.key in ("tab", "enter", "shift+tab"):
            self.action_select()
        elif event.key == "up":
            self.action_cursor_up()
        elif event.key == "down":
            self.action_cursor_down()
        elif event.key == "pageup":
            self.action_page_up()
        elif event.key == "pagedown":
            self.action_page_down()

    @property
    def _parent_container_size(self) -> Size:
        return getattr(self.parent, "container_size", self.screen.container_size)

    @property
    def _width(self) -> int:
        if self.styles.width and self.styles.width.unit == Unit.CELLS:
            return int(self.styles.width.value)
        else:
            return self.outer_size.width

    @staticmethod
    def _get_x_offset(
        prefix_length: int,
        additional_x_offset: int,
        cursor_x: int,
        container_width: int,
        width: int,
    ) -> int:
        x = cursor_x - prefix_length + additional_x_offset
        max_x = container_width - width
        if max_x < 0:
            raise ValueError("doesn't fit")

        return min(x, max_x)

    @staticmethod
    def _get_y_offset(cursor_y: int, height: int, container_height: int) -> int:
        fits_above = height < cursor_y + 1
        fits_below = height < container_height - cursor_y
        if fits_below:
            y = cursor_y + 1
        elif fits_above:
            y = cursor_y - height
        else:
            raise ValueError("Doesn't fit.")

        return y
