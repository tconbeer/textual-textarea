from textual.widgets import Input


class CancellableInput(Input):
    BINDINGS = [("escape", "cancel", "Cancel")]

    def action_cancel(self) -> None:
        self.remove()
