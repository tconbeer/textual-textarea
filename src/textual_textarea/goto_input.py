from __future__ import annotations

from textual.validation import ValidationResult, Validator

from textual_textarea.cancellable_input import CancellableInput


class GotoLineValidator(Validator):
    def __init__(
        self,
        max_line_number: int,
        min_line_number: int = 1,
        failure_description: str = "Not a valid line number.",
    ) -> None:
        super().__init__(failure_description)
        self.max_line_number = max_line_number
        self.min_line_number = min_line_number

    def validate(self, value: str) -> ValidationResult:
        try:
            lno = int(value)
        except (ValueError, TypeError):
            return self.failure("Not a valid line number.")

        if lno < self.min_line_number:
            return self.failure(f"Line number must be >= {self.min_line_number}")
        elif lno > self.max_line_number:
            return self.failure(f"Line number must be <= {self.max_line_number}")

        return self.success()


class GotoLineInput(CancellableInput):
    def __init__(
        self,
        *,
        max_line_number: int,
        id: str | None = None,  # noqa: A002
        classes: str | None = None,
        current_line: int | None = None,
        min_line_number: int = 1,
    ) -> None:
        current_line_text = (
            f"Current line: {current_line}. " if current_line is not None else ""
        )
        range_text = (
            f"Enter a line number between {min_line_number} and " f"{max_line_number}."
        )
        placeholder = f"{current_line_text}{range_text} ESC to cancel."
        super().__init__(
            "",
            placeholder=placeholder,
            type="integer",
            validators=GotoLineValidator(
                max_line_number=max_line_number, min_line_number=min_line_number
            ),
            validate_on=["changed"],
            id=id,
            classes=classes,
        )
