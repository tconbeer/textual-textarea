from __future__ import annotations

import stat
from pathlib import Path

from rich.highlighter import Highlighter
from textual.binding import Binding
from textual.message import Message
from textual.suggester import Suggester
from textual.validation import ValidationResult, Validator
from textual.widgets import Input


def path_completer(prefix: str) -> list[tuple[str, str]]:
    try:
        original = Path(prefix)
        p = original.expanduser()
        if p.is_dir():
            matches = list(p.iterdir())
        else:
            matches = list(p.parent.glob(f"{p.name}*"))
        if original != p and original.parts and original.parts[0] == "~":
            prompts = [str(Path("~") / m.relative_to(Path.home())) for m in matches]
        elif not original.is_absolute() and prefix.startswith("./"):
            prompts = [f"./{m}" for m in matches]
        else:
            prompts = [str(m) for m in matches]
        return [(p, p) for p in prompts]
    except Exception:
        return []


class PathSuggester(Suggester):
    def __init__(self) -> None:
        super().__init__(use_cache=True, case_sensitive=True)

    async def get_suggestion(self, value: str) -> str | None:
        matches = path_completer(value)
        if len(matches) == 1:
            return str(matches[0][0])
        else:
            return None


class PathValidator(Validator):
    def __init__(
        self,
        dir_okay: bool,
        file_okay: bool,
        must_exist: bool,
        failure_description: str = "Not a valid path.",
    ) -> None:
        self.dir_okay = dir_okay
        self.file_okay = file_okay
        self.must_exist = must_exist
        super().__init__(failure_description)

    def validate(self, value: str) -> ValidationResult:
        if self.dir_okay and self.file_okay and not self.must_exist:
            return self.success()
        try:
            p = Path(value).expanduser().resolve()
        except Exception:
            return self.failure("Not a valid path.")

        try:
            st = p.stat()
        except FileNotFoundError:
            if self.must_exist:
                return self.failure("File or directory does not exist.")
            return self.success()

        if not self.dir_okay and stat.S_ISDIR(st.st_mode):
            return self.failure("Path cannot be a directory.")
        elif not self.file_okay and stat.S_ISREG(st.st_mode):
            return self.failure("Path cannot be a regular file.")

        return self.success()


class PathInput(Input):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
        Binding("tab", "complete", "Accept Completion", show=False),
    ]

    class Cancelled(Message):
        """
        Posted when the user presses Esc to cancel the input.
        """

        pass

    def __init__(
        self,
        value: str | None = None,
        placeholder: str = "",
        highlighter: Highlighter | None = None,
        password: bool = False,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
        dir_okay: bool = True,
        file_okay: bool = True,
        must_exist: bool = False,
        tab_advances_focus: bool = False,
    ) -> None:
        self.tab_advances_focus = tab_advances_focus
        super().__init__(
            value,
            placeholder,
            highlighter,
            password,
            suggester=PathSuggester(),
            validators=PathValidator(dir_okay, file_okay, must_exist),
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
        )

    def action_cancel(self) -> None:
        self.post_message(self.Cancelled())

    def action_complete(self) -> None:
        if self._suggestion and self._suggestion != self.value:
            self.action_cursor_right()
        elif self.tab_advances_focus:
            self.app.action_focus_next()

    def _toggle_cursor(self) -> None:
        """Toggle visibility of cursor."""
        if self.app.is_headless:
            self._cursor_visible = True
        else:
            self._cursor_visible = not self._cursor_visible
