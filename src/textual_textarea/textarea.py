from math import ceil, floor
from os.path import expanduser
from typing import List, Tuple, Union

import pyperclip
from rich.console import RenderableType
from rich.style import Style
from rich.syntax import Syntax
from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Input, Static

from textual_textarea.cancellable_input import CancellableInput
from textual_textarea.colors import WidgetColors
from textual_textarea.comments import INLINE_MARKERS
from textual_textarea.containers import FooterContainer, TextContainer
from textual_textarea.error_modal import ErrorModal
from textual_textarea.key_handlers import Cursor, handle_arrow
from textual_textarea.messages import TextAreaCursorMoved, TextAreaScrollOne
from textual_textarea.serde import deserialize_lines, serialize_lines

BRACKETS = {
    "(": ")",
    "[": "]",
    "{": "}",
}
CLOSERS = {'"': '"', "'": "'", **BRACKETS}
TAB_SIZE = 4


class TextInput(Static, can_focus=True):
    DEFAULT_CSS = """
        TextInput {
            height: auto;
            width: auto;
            padding: 0 1;
        }
    """

    lines: reactive[List[str]] = reactive(lambda: list(" "))
    cursor: reactive[Cursor] = reactive(Cursor(0, 0))
    selection_anchor: reactive[Union[Cursor, None]] = reactive(None)
    clipboard: List[str] = list()
    cursor_visible: reactive[bool] = reactive(True)
    use_system_clipboard: bool = True
    language: reactive[Union[str, None]] = reactive(None)

    def __init__(
        self,
        theme_colors: WidgetColors,
        language: Union[str, None] = None,
        theme: str = "monokai",
        use_system_clipboard: bool = True,
    ) -> None:
        super().__init__()
        self.theme_colors = theme_colors
        self.language = language
        self.theme = theme
        self.use_system_clipboard = use_system_clipboard

    def on_mount(self) -> None:
        self.blink_timer = self.set_interval(
            0.5,
            self._toggle_cursor,
            pause=not self.has_focus,
        )

    def on_focus(self) -> None:
        self.cursor_visible = True
        self.blink_timer.reset()
        self._scroll_to_cursor()
        self.update(self._content)

    def on_blur(self) -> None:
        self.blink_timer.pause()
        self.cursor_visible = False
        self.update(self._content)

    def on_mouse_down(self, event: events.MouseDown) -> None:
        """
        Moves the anchor and cursor to the click.
        """
        event.stop()
        self.cursor_visible = True
        self.blink_timer.reset()
        self.selection_anchor = Cursor.from_mouse_event(event)
        self.move_cursor(event.x - 1, event.y)
        self.focus()

    def on_mouse_move(self, event: events.MouseMove) -> None:
        """
        Updates the cursor if the button is pressed while the mouse
        is moving.
        """
        if event.button == 1:
            self.move_cursor(event.x - 1, event.y)

    def on_mouse_up(self, event: events.MouseUp) -> None:
        """
        Moves the cursor to the click.
        """
        event.stop()
        self.cursor_visible = True
        self.blink_timer.reset()
        if self.selection_anchor == Cursor.from_mouse_event(event):
            # simple click
            self.selection_anchor = None
        else:
            self.move_cursor(event.x - 1, event.y)
        self.focus()

    def on_click(self, event: events.Click) -> None:
        """
        Click duplicates MouseUp and MouseDown, so we just capture and kill this event.
        """
        event.stop()

    def on_paste(self, event: events.Paste) -> None:
        """
        If the user hits ctrl+v, we don't get that keypress;
        we get a Paste event instead.

        This ignores the contents of the Paste message and mimics the behavior of
        ctrl+u.
        """
        event.stop()
        self.cursor_visible = True
        self.blink_timer.reset()
        self._insert_clipboard_at_selection(self.selection_anchor, self.cursor)
        self.selection_anchor = None
        self.update(self._content)

    def on_key(self, event: events.Key) -> None:
        self.cursor_visible = True
        self.blink_timer.reset()
        selection_before = self.selection_anchor

        # set selection_anchor if it's unset
        if event.key == "shift+delete":
            pass  # todo: shift+delete should delete the whole line
        elif event.key == "shift+tab":
            pass
        elif event.key in (
            "ctrl+underscore",
            "ctrl+`",
            "ctrl+@",
            "ctrl+s",
            "ctrl+c",
            "f1",
            "f2",
            "f3",
            "f4",
            "f5",
            "f6",
            "f7",
            "f8",
            "f9",
            "f10",
            "f11",
            "f12",
        ):
            pass  #  these should maintain selection
        elif event.key == "ctrl+a":
            self.selection_anchor = Cursor(0, 0)
        elif selection_before is None and "shift" in event.key:
            self.selection_anchor = self.cursor
        elif selection_before is not None and "shift" not in event.key:
            self.selection_anchor = None

        # set cursor and modify lines if necessary
        if event.key in (
            "apostrophe",
            "quotation_mark",
            "left_parenthesis",
            "left_square_bracket",
            "left_curly_bracket",
            "right_parenthesis",
            "right_square_bracket",
            "right_curly_bracket",
        ):
            assert event.character is not None
            if selection_before is None:
                self._insert_closed_character_at_cursor(event.character, self.cursor)
            elif event.key in (
                "right_parenthesis",
                "right_square_bracket",
                "right_curly_bracket",
            ):
                self._delete_selection(selection_before, self.cursor)
                self._insert_character_at_cursor(event.character, self.cursor)
                self.cursor = Cursor(
                    lno=self.cursor.lno, pos=self.cursor.pos + len(event.character)
                )
            else:
                self._insert_characters_around_selection(
                    event.character, selection_before, self.cursor
                )
        elif event.key in ("pageup", "shift+pageup"):
            event.stop()
            self.move_cursor(
                x=self.cursor.pos, y=(self.cursor.lno - self._visible_height() + 1)
            )
        elif event.key in ("pagedown", "shift+pagedown"):
            event.stop()
            self.move_cursor(
                x=self.cursor.pos, y=(self.cursor.lno + self._visible_height() - 1)
            )
        elif event.key in ("ctrl+up", "ctrl+down"):
            event.stop()
            self.post_message(TextAreaScrollOne(direction=event.key.split("+")[1]))
        elif any([dir in event.key for dir in ["left", "right", "up", "down"]]):
            event.stop()
            self.cursor = handle_arrow(event.key, self.lines, self.cursor)
        elif event.key in ("home", "shift+home"):
            event.stop()
            self.cursor = Cursor(self.cursor.lno, 0)
        elif event.key in ("end", "shift+end"):
            event.stop()
            self.cursor = Cursor(self.cursor.lno, len(self.lines[self.cursor.lno]) - 1)
        elif event.key == "ctrl+home":
            event.stop()
            self.cursor = Cursor(0, 0)
        elif event.key in ("ctrl+end", "ctrl+a"):
            event.stop()
            self.cursor = Cursor(lno=len(self.lines) - 1, pos=len(self.lines[-1]) - 1)
        elif event.key == "ctrl+underscore":  # actually ctrl+/
            event.stop()
            if self.inline_comment_marker:
                lines, first, last = self._get_selected_lines(selection_before)
                stripped_lines = [line.lstrip() for line in lines]
                indents = [len(line) - len(line.lstrip()) for line in lines]
                if all(
                    [
                        line.startswith(self.inline_comment_marker)
                        for line in stripped_lines
                    ]
                ):
                    no_comment_lines = [
                        line[len(self.inline_comment_marker) :].lstrip()
                        for line in stripped_lines
                    ]
                    self.lines[first.lno : last.lno + 1] = [
                        f"{' ' * indent}{line}"
                        for indent, line in zip(indents, no_comment_lines)
                    ]
                else:
                    self.lines[first.lno : last.lno + 1] = [
                        f"{' ' * indent}{self.inline_comment_marker} {stripped_line}"
                        for indent, stripped_line in zip(indents, stripped_lines)
                    ]
        elif event.key in ("ctrl+c", "ctrl+x"):
            event.stop()
            if selection_before:
                lines, first, last = self._get_selected_lines(selection_before)
            else:  # no selection, copy whole line
                lines, first, last = (
                    [self.lines[self.cursor.lno], ""],
                    Cursor(self.cursor.lno, 0),
                    Cursor(self.cursor.lno, len(self.lines[self.cursor.lno])),
                )
            lines[-1] = lines[-1][: last.pos]
            lines[0] = lines[0][first.pos :]
            self.clipboard = lines.copy()
            if self.use_system_clipboard:
                try:
                    pyperclip.copy(serialize_lines(self.clipboard))
                except pyperclip.PyperclipException:
                    # no system clipboard; common in CI runners
                    pass
            self.log(f"copied to clipboard: {self.clipboard}")
            if event.key == "ctrl+x":
                self._delete_selection(first, last)
                new_lno = min(first.lno, len(self.lines) - 1)
                self.cursor = Cursor(
                    new_lno, min(first.pos, len(self.lines[new_lno]) - 1)
                )
        elif event.key in ("ctrl+u", "ctrl+v"):
            event.stop()
            self._insert_clipboard_at_selection(selection_before, self.cursor)
        elif event.key == "tab":
            event.stop()
            lines, first, last = self._get_selected_lines(selection_before)
            # in some cases, selections are replaced with four spaces
            if first.lno == last.lno and (
                first.pos == last.pos
                or first.pos != 0
                or last.pos != len(self.lines[self.cursor.lno]) - 1
            ):
                self._delete_selection(first, last)
                indent = TAB_SIZE - first.pos % TAB_SIZE
                self._insert_character_at_cursor(" " * indent, first)
                self.cursor = Cursor(lno=first.lno, pos=first.pos + indent)
            # usually, selected lines are prepended with four-ish spaces
            else:
                self._indent_selection(selection_before, self.cursor, kind="indent")
        elif event.key == "shift+tab":
            event.stop()
            self._indent_selection(selection_before, self.cursor, kind="dedent")
        elif event.key == "enter":
            event.stop()
            old_lines, first, last = self._get_selected_lines(selection_before)
            head = f"{old_lines[0][:first.pos]} "
            tail = f"{old_lines[-1][last.pos:]}"
            if old_lines[0].isspace():
                indent = 0
            else:
                indent = len(old_lines[0]) - len(old_lines[0].lstrip())

            char_before = self._get_character_before_cursor(first)
            if char_before in BRACKETS and BRACKETS[
                char_before
            ] == self._get_character_at_cursor(last):
                new_indent = indent + TAB_SIZE - (indent % TAB_SIZE)
                self.lines[first.lno : last.lno + 1] = [
                    head,
                    f"{' ' * new_indent} ",
                    f"{' ' * indent}{tail.lstrip()}",
                ]
                self.cursor = Cursor(first.lno + 1, new_indent)
            else:
                self.lines[first.lno : last.lno + 1] = [
                    head,
                    f"{' ' * indent}{tail.lstrip() or ' '}",
                ]
                self.cursor = Cursor(first.lno + 1, min(first.pos, indent))
        elif event.key == "delete":
            event.stop()
            if selection_before is None:
                anchor = self.cursor
                cursor = handle_arrow("right", self.lines, self.cursor)
            else:
                anchor = selection_before
                cursor = self.cursor
            self._delete_selection(anchor, cursor)
        elif event.key == "backspace":
            event.stop()
            if selection_before is None:
                anchor = self.cursor
                cursor = handle_arrow("left", self.lines, self.cursor)
            else:
                anchor = selection_before
                cursor = self.cursor
            self._delete_selection(anchor, cursor)

        elif event.is_printable:
            event.stop()
            assert event.character is not None
            if selection_before is not None:
                self._delete_selection(selection_before, self.cursor)
            self._insert_character_at_cursor(event.character, self.cursor)
            self.cursor = Cursor(
                lno=self.cursor.lno, pos=self.cursor.pos + len(event.character)
            )

        self.update(self._content)

    def watch_cursor(self) -> None:
        self._scroll_to_cursor()

    def watch_language(self, language: str) -> None:
        self.inline_comment_marker = INLINE_MARKERS.get(language)

    @property
    def _content(self) -> RenderableType:
        syntax = Syntax(
            "\n".join(self.lines),
            lexer=self.language,
            theme=self.theme,
        )
        if self.cursor_visible:
            syntax.stylize_range(
                "reverse",
                # rows are 1-indexed
                (self.cursor.lno + 1, self.cursor.pos),
                (self.cursor.lno + 1, self.cursor.pos + 1),
            )
        if self.selection_anchor is not None:
            first = min(self.selection_anchor, self.cursor)
            second = max(self.selection_anchor, self.cursor)
            selection_style = Style(
                bgcolor=self.theme_colors.selection_bgcolor.rich_color
            )
            syntax.stylize_range(
                selection_style,
                # rows are 1-indexed
                (first.lno + 1, first.pos),
                (second.lno + 1, second.pos),
            )
        return syntax

    def _scroll_to_cursor(self) -> None:
        self.post_message(TextAreaCursorMoved(self.cursor.pos, self.cursor.lno))

    def _visible_height(self) -> int:
        parent = self.parent
        assert isinstance(parent, TextContainer)
        return parent.window_region.height

    def _toggle_cursor(self) -> None:
        self.cursor_visible = not self.cursor_visible
        self.update(self._content)

    def _get_selected_lines(
        self,
        maybe_anchor: Union[Cursor, None],
        maybe_cursor: Union[Cursor, None] = None,
    ) -> Tuple[List[str], Cursor, Cursor]:
        """
        Returns a tuple of:
         - the lines between (inclusive) the optional selection anchor and the cursor,
         - the first of either the cursor or anchor
         - the last of either the cursor or anchor
        """
        cursor = maybe_cursor or self.cursor
        anchor = maybe_anchor or cursor
        first = min(anchor, cursor)
        last = max(anchor, cursor)
        return self.lines[first.lno : last.lno + 1], first, last

    def _insert_character_at_cursor(self, character: str, cursor: Cursor) -> None:
        line = self.lines[cursor.lno]
        new_line = f"{line[:cursor.pos]}{character}{line[cursor.pos:]}"
        self.lines[cursor.lno] = new_line

    def _insert_characters_around_selection(
        self, character: str, anchor: Cursor, cursor: Cursor
    ) -> None:
        first = min(anchor, cursor)
        last = max(anchor, cursor)
        self._insert_character_at_cursor(character, first)
        if first.lno == last.lno:
            self.cursor = Cursor(lno=last.lno, pos=last.pos + len(character))
        else:
            self.cursor = last
        self._insert_character_at_cursor(CLOSERS[character], self.cursor)

    def _insert_closed_character_at_cursor(
        self, character: str, cursor: Cursor
    ) -> None:
        if self._get_character_at_cursor(cursor) == character:
            self.cursor = Cursor(cursor.lno, cursor.pos + 1)
        else:
            prev = self._get_character_before_cursor(cursor)
            self._insert_character_at_cursor(character, cursor)
            self.cursor = Cursor(cursor.lno, cursor.pos + len(character))
            if (
                character in CLOSERS
                and self.cursor.pos == len(self.lines[self.cursor.lno]) - 1
                and (prev is None or prev == " " or character in BRACKETS)
            ):
                self._insert_character_at_cursor(CLOSERS[character], self.cursor)

    def _delete_selection(self, anchor: Cursor, cursor: Cursor) -> None:
        old_lines, first, last = self._get_selected_lines(anchor, maybe_cursor=cursor)
        head = f"{old_lines[0][:first.pos]}"
        tail = f"{old_lines[-1][last.pos:]}"
        if new_line := f"{head}{tail}":
            self.lines[first.lno : last.lno + 1] = [new_line]
        else:  # empty str, no line-ending space, delete whole line
            self.lines[first.lno : last.lno + 1] = []
            if not self.lines:
                self.lines = [" "]
        self.cursor = Cursor(first.lno, first.pos)

    def _indent_selection(
        self, anchor: Union[Cursor, None], cursor: Cursor, kind: str
    ) -> None:
        assert kind in ("indent", "dedent")
        rounder, offset = (ceil, -1) if kind == "dedent" else (floor, 1)

        lines, first, last = self._get_selected_lines(anchor, cursor)
        leading_spaces = [(len(line) - len(line.lstrip())) for line in lines]
        leading_tabs = [rounder(space / TAB_SIZE) for space in leading_spaces]
        new_lines = [
            f"{' ' * TAB_SIZE * max(0, indent+offset)}{line.lstrip()}"
            for line, indent in zip(lines, leading_tabs)
        ]
        self.lines[first.lno : last.lno + 1] = new_lines
        if anchor:
            change_at_anchor_line = len(new_lines[anchor.lno - first.lno]) - len(
                lines[anchor.lno - first.lno]
            )
            self.selection_anchor = (
                anchor
                if anchor.pos == 0
                else Cursor(
                    anchor.lno,
                    anchor.pos + change_at_anchor_line,
                )
            )
        change_at_cursor = len(new_lines[cursor.lno - first.lno]) - len(
            lines[cursor.lno - first.lno]
        )
        self.cursor = (
            cursor
            if cursor.pos == 0
            else Cursor(cursor.lno, cursor.pos + change_at_cursor)
        )

    def _insert_clipboard_at_selection(
        self, anchor: Union[Cursor, None], cursor: Cursor
    ) -> None:
        if self.use_system_clipboard:
            try:
                sys_clipboard = pyperclip.paste()
            except pyperclip.PyperclipException:
                # no system clipboard; common in CI runners
                pass
            else:
                self.clipboard = deserialize_lines(sys_clipboard, trim=True)
        if anchor:
            self._delete_selection(anchor, cursor)
            cursor = self.cursor
        head = self.lines[cursor.lno][: cursor.pos]
        tail = self.lines[cursor.lno][cursor.pos :]
        if (clip_len := len(self.clipboard)) != 0:
            new_lines = self.clipboard.copy()
            new_lines[0] = f"{head}{new_lines[0]}"
            new_lines[-1] = f"{new_lines[-1]}{tail}"
            self.lines[cursor.lno : cursor.lno + 1] = new_lines
            self.cursor = Cursor(
                cursor.lno + clip_len - 1,
                len(self.lines[cursor.lno + clip_len - 1]) - len(tail),
            )

    def _get_character_at_cursor(self, cursor: Cursor) -> str:
        return self.lines[cursor.lno][cursor.pos]

    def _get_character_before_cursor(self, cursor: Cursor) -> Union[str, None]:
        if self.cursor.pos == 0:
            return None
        else:
            return self.lines[cursor.lno][cursor.pos - 1]

    def move_cursor(self, x: int, y: int) -> None:
        max_y = len(self.lines) - 1
        safe_y = max(0, min(max_y, y))
        max_x = len(self.lines[safe_y]) - 1
        safe_x = max(0, min(max_x, x))
        self.cursor = Cursor(lno=safe_y, pos=safe_x)
        self.update(self._content)


class TextArea(Widget, can_focus=True, can_focus_children=False):
    """
    A Widget that presents a feature-rich, multiline text editor interface.

    Attributes:
        text (str): The contents of the TextArea
        language (str): Must be the short name of a Pygments lexer
            (https://pygments.org/docs/lexers/), e.g., "python", "sql", "as3".
        theme (str): Must be name of a Pygments style (https://pygments.org/styles/),
            e.g., "bw", "github-dark", "solarized-light".
        theme_colors (WidgetColors): The colors extracted from the theme.
    """

    BINDINGS = [
        Binding("ctrl+s", "save", "Save Query"),
        Binding("ctrl+o", "load", "Open Query"),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    def __init__(
        self,
        *children: Widget,
        name: Union[str, None] = None,
        id: Union[str, None] = None,
        classes: Union[str, None] = None,
        disabled: bool = False,
        language: Union[str, None] = None,
        theme: str = "monokai",
        use_system_clipboard: bool = True,
    ) -> None:
        """
        Initializes an instance of a TextArea.

        Args:
            (see also textual.widget.Widget)
            language (str): Must be the short name of a Pygments lexer
                (https://pygments.org/docs/lexers/), e.g., "python", "sql", "as3".
            theme (str): Must be name of a Pygments style (https://pygments.org/styles/),
                e.g., "bw", "github-dark", "solarized-light".
        """
        super().__init__(
            *children, name=name, id=id, classes=classes, disabled=disabled
        )
        self._language = language
        self.theme = theme
        self.theme_colors = WidgetColors.from_theme(self.theme)
        self.use_system_clipboard = use_system_clipboard

    @property
    def text(self) -> str:
        """
        Returns:
            (str) The contents of the TextArea.
        """
        return serialize_lines(self.text_input.lines)

    @text.setter
    def text(self, contents: str) -> None:
        """
        Args:
            contents (str): A string (optionally containing newlines) to
                set the contents of the TextArea equal to.
        """
        self.text_input.move_cursor(0, 0)
        self.text_input.lines = deserialize_lines(contents)

    @property
    def cursor(self) -> Cursor:
        """
        Returns
            Cursor: The location of the cursor in the TextInput
        """
        return self.text_input.cursor

    @cursor.setter
    def cursor(self, cursor: Union[Cursor, Tuple[int, int]]) -> None:
        """
        Args:
            cursor (Union[Cursor, Tuple[int, int]]): The position (line number, pos)
            to move the cursor to
        """
        self.text_input.move_cursor(cursor[1], cursor[0])

    @property
    def language(self) -> Union[str, None]:
        """
        Returns
            str | None: The Pygments short name of the active language
        """
        return self.text_input.language

    @language.setter
    def language(self, language: str) -> None:
        """
        Args:
            langage (str | None): The Pygments short name for the new language
        """
        self.text_input.language = language

    def compose(self) -> ComposeResult:
        with TextContainer():
            yield TextInput(
                language=self._language,
                theme=self.theme,
                theme_colors=self.theme_colors,
            )
        yield FooterContainer(theme_colors=self.theme_colors)

    def on_mount(self) -> None:
        self.styles.background = self.theme_colors.bgcolor
        self.text_container = self.query_one(TextContainer)
        self.text_input = self.query_one(TextInput)
        self.footer = self.query_one(FooterContainer)

    def on_focus(self) -> None:
        self.text_input.focus()

    def action_save(self) -> None:
        self._mount_footer_input("save")

    def action_load(self) -> None:
        self._mount_footer_input("open")

    def _mount_footer_input(self, name: str) -> None:
        input = CancellableInput(
            id=f"textarea__{name}_input",
            placeholder=f"{name.capitalize()}: Enter file path OR press ESC to cancel",
        )
        input.styles.background = self.theme_colors.bgcolor
        input.styles.border = "round", self.theme_colors.contrast_text_color
        input.styles.color = self.theme_colors.contrast_text_color
        self.footer.mount(input)
        input.focus()

    def on_text_area_cursor_moved(self, event: TextAreaCursorMoved) -> None:
        """
        Scrolls the container so the cursor is visible.
        """
        event.stop()
        container = self.text_container
        x_buffer = max(container.window_region.width // 6, 2)
        y_buffer = max(container.window_region.height // 6, 2)
        if event.cursor_x < container.window_region.x + x_buffer:  # scroll left
            container.scroll_to(event.cursor_x - x_buffer, container.window_region.y)
        elif (
            event.cursor_x
            >= container.window_region.x + container.window_region.width - x_buffer
        ):  # scroll right
            container.scroll_to(
                event.cursor_x - container.window_region.width + x_buffer,
                container.window_region.y,
            )
        if event.cursor_y < container.window_region.y + y_buffer:  # scroll up
            container.scroll_to(container.window_region.x, event.cursor_y - y_buffer)
        elif (
            event.cursor_y
            >= container.window_region.y + container.window_region.height - y_buffer
        ):  # scroll down
            container.scroll_to(
                container.window_region.x,
                event.cursor_y - container.window_region.height + y_buffer,
            )
        self.text_input.update(self.text_input._content)

    def on_text_area_scroll_one(self, event: TextAreaScrollOne) -> None:
        event.stop()
        offset = 1 if event.direction == "down" else -1
        self.text_container.scroll_to(
            self.text_container.window_region.x,
            self.text_container.window_region.y + offset,
        )

    def on_input_submitted(self, message: Input.Submitted) -> None:
        """
        Handle the submit event for the Save and Open modals.
        """
        expanded_path = expanduser(message.input.value)
        if message.input.id == "textarea__save_input":
            try:
                with open(expanded_path, "w") as f:
                    f.write(self.text)
            except OSError as e:
                self.app.push_screen(
                    ErrorModal(
                        title="Save File Error",
                        header=(
                            "There was an error when attempting to save your file:"
                        ),
                        error=e,
                    )
                )
        elif message.input.id == "textarea__open_input":
            try:
                with open(expanded_path, "r") as f:
                    contents = f.read()
            except OSError as e:
                self.app.push_screen(
                    ErrorModal(
                        title="Open File Error",
                        header=(
                            "There was an error when attempting to open your file:"
                        ),
                        error=e,
                    )
                )
            else:
                self.text = contents
        message.input.remove()
        self.text_input.update(self.text_input._content)
        self.text_input.focus()
