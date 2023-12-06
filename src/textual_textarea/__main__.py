import sys
from itertools import cycle

from pygments.styles import get_all_styles
from textual.app import App, ComposeResult

from textual_textarea import TextArea
from textual_textarea.next import TextArea as TextAreaNext


class TextApp(App, inherit_bindings=False):
    def compose(self) -> ComposeResult:
        try:
            language = sys.argv[1]
        except IndexError:
            language = "python"
        yield TextArea(
            language=language, theme="zenburn", use_system_clipboard=True, id="ta"
        )

    def on_mount(self) -> None:
        ta = self.query_one("#ta")
        ta.focus()


class NextApp(App, inherit_bindings=False):
    def compose(self) -> ComposeResult:
        try:
            language = sys.argv[1]
        except IndexError:
            language = "sql"
        yield TextAreaNext(
            language=language, theme="fruity", use_system_clipboard=True, id="ta"
        )

    def on_mount(self) -> None:
        self.style_cycle = cycle(list(get_all_styles()))
        self.ta = self.query_one("#ta", expect_type=TextAreaNext)
        self.ta.text = """
        select *, 1, 'a', "a", sum(a)
        from foo
        where a = b and c is true
        """
        self.ta.focus()
        self.set_interval(2, self.change_color)

    def change_color(self) -> None:
        self.ta.theme = next(self.style_cycle)


app = NextApp()
# app = TextApp()
app.run()
