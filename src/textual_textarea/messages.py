from pathlib import Path
from typing import Union

from textual.message import Message


class TextAreaCursorMoved(Message, bubble=True):
    """Posted when the cursor moves

    Attributes:
        cursor_x: The x position of the cursor
        cursor_y: The y position (line number)
    """

    def __init__(self, cursor_x: int, cursor_y: int) -> None:
        super().__init__()
        self.cursor_x = cursor_x
        self.cursor_y = cursor_y


class TextAreaScrollOne(Message, bubble=True):
    """
    Posted to get parent container to scroll one in a direction
    """

    def __init__(self, direction: str) -> None:
        super().__init__()
        assert direction in ("up", "down")
        self.direction = direction


class TextAreaClipboardError(Message, bubble=True):
    """
    Posted when textarea cannot access the system clipboard
    """

    def __init__(self, action: str) -> None:
        super().__init__()
        self.action = action


class TextAreaSaved(Message, bubble=True):
    """
    Posted when the textarea saved a file successfully.
    """

    def __init__(self, path: Union[Path, str]) -> None:
        self.path = str(path)
        super().__init__()
