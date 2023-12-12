from typing import NamedTuple, Union

from textual.events import MouseEvent


class Cursor(NamedTuple):
    lno: int
    pos: int
    pref_pos: Union[int, None] = None

    @classmethod
    def from_mouse_event(cls, event: MouseEvent) -> "Cursor":
        return Cursor(event.y, event.x - 1)
