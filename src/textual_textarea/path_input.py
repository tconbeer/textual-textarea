import stat
from pathlib import Path
from typing import Union

from rich.highlighter import Highlighter
from textual.message import Message
from textual.suggester import Suggester
from textual.validation import ValidationResult, Validator
from textual.widgets import Input


class CancelPathInput(Message):
    pass


class PathSuggester(Suggester):
    def __init__(self) -> None:
        super().__init__(use_cache=True, case_sensitive=True)

    async def get_suggestion(self, value: str) -> Union[str, None]:
        try:
            p = Path(value).expanduser()
            matches = list(p.parent.glob(f"{p.parts[-1]}*"))
            if len(matches) == 1:
                return str(matches[0])
            else:
                return None
        except Exception:
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
        ("escape", "cancel", "Cancel"),
        ("tab", "complete", "Accept Completion"),
    ]

    def __init__(
        self,
        value: Union[str, None] = None,
        placeholder: str = "",
        highlighter: Union[Highlighter, None] = None,
        password: bool = False,
        *,
        name: Union[str, None] = None,
        id: Union[str, None] = None,
        classes: Union[str, None] = None,
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
        self.post_message(CancelPathInput())

    def action_complete(self) -> None:
        if self._suggestion and self._suggestion != self.value:
            self.action_cursor_right()
        elif self.tab_advances_focus:
            self.app.action_focus_next()
