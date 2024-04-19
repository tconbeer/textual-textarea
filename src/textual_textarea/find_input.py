from __future__ import annotations

from textual_textarea.cancellable_input import CancellableInput


class FindInput(CancellableInput):
    def __init__(self, value: str = "") -> None:
        super().__init__(
            value=value,
            placeholder="Find; Enter for next; ESC to close",
            password=False,
            type="text",
            id="textarea__find_input",
        )
