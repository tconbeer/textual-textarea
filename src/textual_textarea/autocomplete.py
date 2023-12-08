from __future__ import annotations

from typing import Callable

from rich.console import RenderableType
from textual import work
from textual.css.scalar import ScalarOffset
from textual.events import Key, Resize
from textual.message import Message
from textual.reactive import Reactive, reactive
from textual.widget import Widget
from textual.widgets import OptionList

from textual_textarea.messages import TextAreaHideCompletionList


class CompletionList(OptionList, can_focus=False, inherit_bindings=False):
    DEFAULT_CSS = """
    CompletionList {
        layer: overlay;
        padding: 0;
        border: none;
        width: 30;
        max-height: 8;
        display: none;
    }
    CompletionList.open {
        display: block;
    }
    """

    class CompletionsReady(Message, bubble=False):
        def __init__(self, prefix: str, items: list[RenderableType]) -> None:
            super().__init__()
            self.items = items
            self.prefix = prefix

    open: Reactive[bool] = reactive(False)
    cursor_screen_offset: tuple[int, int] = (0, 0)
    prefix: str = ""

    def on_completion_list_completions_ready(self, event: CompletionsReady) -> None:
        event.stop()
        self.prefix = event.prefix
        self.clear_options()
        self.add_options(items=event.items)
        self.action_first()
        self.open = True

    def watch_open(self, open: bool) -> None:
        if open:
            self.add_class("open")
        else:
            self.remove_class("open")

    def on_resize(self, event: Resize) -> None:
        try:
            self.styles.offset = self._get_list_offset(
                width=event.size.width, height=event.size.height
            )
        except ValueError:
            self.open = False

    @work(thread=True, exclusive=True, group="completers")
    def show_completions(
        self, prefix: str, completer: Callable[[str], list[RenderableType]] | None
    ) -> None:
        matches = completer(prefix) if completer is not None else []
        self.log("MATCHES: ", matches)
        if matches:
            self.post_message(
                self.CompletionsReady(
                    prefix=prefix, items=sorted(matches, key=lambda x: str(x))
                )
            )
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
        cursor_x = self.cursor_screen_offset[0] - prefix_length
        if isinstance(self.parent, Widget):
            container_size = self.parent.container_size
        else:
            container_size = self.screen.container_size

        max_x = container_size.width - width

        cursor_y = self.cursor_screen_offset[1]
        fits_above = cursor_y > height + 1
        fits_below = container_size.height - cursor_y > height + 1
        if fits_below:
            y = cursor_y + 1
        elif fits_above:
            y = cursor_y - height
        else:
            raise ValueError("Doesn't fit.")

        return ScalarOffset.from_offset((min(cursor_x, max_x), y))
