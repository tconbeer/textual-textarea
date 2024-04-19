from __future__ import annotations

from textual import on
from textual.events import Blur, Key
from textual.widgets import Input

from textual_textarea.cancellable_input import CancellableInput


class FindInput(CancellableInput):
    def __init__(self, value: str = "", history: list[str] | None = None) -> None:
        super().__init__(
            value=value,
            placeholder="Find; enter for next; ESC to close; ↑↓ for history",
            password=False,
            type="text",
            id="textarea__find_input",
        )
        self.history: list[str] = [] if history is None else history
        self.history_index: int | None = None

    @on(Key)
    def handle_special_keys(self, event: Key) -> None:
        if event.key not in ("up", "down", "f3"):
            self.history_index = None
            return
        event.stop()
        event.prevent_default()
        if event.key == "down":
            self._handle_down()
        elif event.key == "up":
            self._handle_up()
        elif event.key == "f3":
            self.post_message(Input.Submitted(self, self.value))

    @on(Blur)
    def handle_blur(self) -> None:
        if self.value and (not self.history or self.value != self.history[-1]):
            self.history.append(self.value)

    def _handle_down(self) -> None:
        if self.history_index is None:
            self.checkpoint()
            self.value = ""
        elif self.history_index == -1:
            self.history_index = None
            self.value = ""
        else:
            self.history_index += 1
            self.value = self.history[self.history_index]
            self.action_end()

    def checkpoint(self) -> bool:
        if self.value and (not self.history or self.value != self.history[-1]):
            self.history.append(self.value)
            return True
        return False

    def _handle_up(self) -> None:
        if not self.history:
            if self.value:
                self.history.append(self.value)
            self.value = ""
            return

        if self.history_index is None:
            self.history_index = -1 if self.checkpoint() else 0

        self.history_index = max(-1 * len(self.history), self.history_index - 1)
        self.value = self.history[self.history_index]
        self.action_end()
