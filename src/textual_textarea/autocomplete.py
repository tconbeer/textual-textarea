from __future__ import annotations

from typing import Callable

from rich.console import RenderableType
from textual import work
from textual.css.scalar import Scalar, ScalarOffset, Unit
from textual.events import Key, Resize
from textual.message import Message
from textual.reactive import Reactive, reactive
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
        def __init__(
            self, prefix: str, items: list[tuple[RenderableType, str]]
        ) -> None:
            super().__init__()
            self.items = items
            self.prefix = prefix

    open: Reactive[bool] = reactive(False)
    cursor_offset: tuple[int, int] = (0, 0)
    prefix: str = ""
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

    def on_completion_list_completions_ready(self, event: CompletionsReady) -> None:
        INNER_CONTENT_WIDTH = 37
        event.stop()
        self.prefix = event.prefix
        self.clear_options()

        # if the completions' prompts are wider than the widget,
        # we have to trunctate them
        prompts = [item[0] for item in event.items]
        max_length = max(map(len, map(str, prompts)))
        if max_length > INNER_CONTENT_WIDTH:
            truncate_amount = min(
                max_length - INNER_CONTENT_WIDTH, len(event.prefix) - 2
            )
            self.additional_x_offset = truncate_amount - 1
            items = [
                Completion(prompt=f"…{str(item[0])[truncate_amount:]}", value=item[1])
                for item in event.items
            ]
        else:
            self.additional_x_offset = 0
            items = [Completion(prompt=item[0], value=item[1]) for item in event.items]

        self.add_options(items=items)
        self.action_first()
        self.open = True

    def watch_open(self, open: bool) -> None:
        if open:
            self.add_class("open")
            self.styles.max_height = Scalar(
                value=8.0, unit=Unit.CELLS, percent_unit=Unit.PERCENT
            )
        else:
            self.remove_class("open")

    def on_resize(self, event: Resize) -> None:
        try:
            self.styles.offset = self._get_list_offset(
                width=event.size.width, height=event.size.height
            )
        except ValueError:
            if self.styles.max_height is not None and self.styles.max_height.value > 1:
                self.styles.max_height = Scalar(
                    value=self.styles.max_height.value - 1,
                    unit=self.styles.max_height.unit,
                    percent_unit=self.styles.max_height.percent_unit,
                )
            else:
                self.open = False

    @work(thread=True, exclusive=True, group="completers")
    def show_completions(
        self,
        prefix: str,
        completer: Callable[[str], list[tuple[RenderableType, str]]] | None,
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
            self.action_page_up()  # type: ignore
        elif event.key == "pagedown":
            self.action_page_down()  # type: ignore

    def _get_list_offset(self, width: int, height: int) -> ScalarOffset:
        prefix_length = len(self.prefix)
        cursor_x, cursor_y = self.cursor_offset
        container_size = getattr(
            self.parent, "container_size", self.screen.container_size
        )

        x = cursor_x - prefix_length + self.additional_x_offset
        max_x = container_size.width - width

        fits_above = cursor_y + 1 > height
        fits_below = container_size.height - cursor_y > height
        if fits_below:
            y = cursor_y + 1
        elif fits_above:
            y = cursor_y - height
        else:
            raise ValueError("Doesn't fit.")

        return ScalarOffset.from_offset((min(x, max_x), y))
