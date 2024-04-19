from textual.binding import Binding
from textual.message import Message
from textual.widgets import Input


class CancellableInput(Input):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    class Cancelled(Message):
        """
        Posted when the user presses Esc to cancel the input.
        """

        pass

    def action_cancel(self) -> None:
        self.post_message(self.Cancelled())
