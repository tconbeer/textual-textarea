from __future__ import annotations

import re
from contextlib import suppress
from math import ceil, floor
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Literal, Sequence

import pyperclip
from rich.console import RenderableType
from textual import events, on, work
from textual._cells import cell_len
from textual.app import ComposeResult
from textual.binding import Binding
from textual.events import Paste
from textual.message import Message
from textual.reactive import Reactive, reactive
from textual.timer import Timer
from textual.widget import Widget
from textual.widgets import Input, Label, OptionList, TextArea
from textual.widgets.text_area import Location, Selection, SyntaxAwareDocument

from textual_textarea.autocomplete import CompletionList
from textual_textarea.cancellable_input import CancellableInput
from textual_textarea.colors import WidgetColors, text_area_theme_from_pygments_name
from textual_textarea.comments import INLINE_MARKERS
from textual_textarea.containers import FooterContainer, TextContainer
from textual_textarea.error_modal import ErrorModal
from textual_textarea.find_input import FindInput
from textual_textarea.goto_input import GotoLineInput
from textual_textarea.messages import (
    TextAreaClipboardError,
    TextAreaHideCompletionList,
    TextAreaSaved,
)
from textual_textarea.path_input import PathInput, path_completer

if TYPE_CHECKING:
    from tree_sitter import Node, Parser, Query, Tree

BRACKETS = {
    "(": ")",
    "[": "]",
    "{": "}",
}
CLOSERS = {'"': '"', "'": "'", **BRACKETS}

# these patterns need to match a reversed string!
DOUBLE_QUOTED_EXPR = r'"([^"\\]*(\\.[^"\\]*|""[^"\\]*)*)"(b?r|f|b|rb|&?u|@)?'
SINGLE_QUOTED_EXPR = r"'([^'\\]*(\\.[^'\\]*|''[^'\\]*)*)'(b?r|f|b|rb|&?u|x)?"
BACKTICK_EXPR = r"`([^`\\]*(\\.[^`\\]*)*)`"
PATH_PROG = re.compile(r"[^\"\'\s]+")
MEMBER_PROG = re.compile(
    rf"\w*(`|'|\")?(\.|::?)(\w+|{SINGLE_QUOTED_EXPR}|{DOUBLE_QUOTED_EXPR}|{BACKTICK_EXPR})",
    flags=re.IGNORECASE,
)
WORD_PROG = re.compile(r"\w+")
NON_WORD_CHAR_PROG = re.compile(r"\W")


class TextAreaPlus(TextArea, inherit_bindings=False):
    DEFAULT_CSS = """
    TextAreaPlus {
        width: 1fr;
        height: 1fr;
        border: none;
        layer: main;

        &:focus {
            border: none;
        }
    }
    """
    BINDINGS = [
        # Cursor movement
        Binding("up", "cursor_up", "cursor up", show=False),
        Binding("down", "cursor_down", "cursor down", show=False),
        Binding("left", "cursor_left", "cursor left", show=False),
        Binding("right", "cursor_right", "cursor right", show=False),
        Binding("ctrl+left", "cursor_word_left", "cursor word left", show=False),
        Binding("ctrl+right", "cursor_word_right", "cursor word right", show=False),
        Binding("home", "cursor_line_start", "cursor line start", show=False),
        Binding("end", "cursor_line_end", "cursor line end", show=False),
        Binding("ctrl+home", "cursor_doc_start", "cursor doc start", show=False),
        Binding("ctrl+end", "cursor_doc_end", "cursor doc end", show=False),
        Binding("pageup", "cursor_page_up", "cursor page up", show=False),
        Binding("pagedown", "cursor_page_down", "cursor page down", show=False),
        # scrolling
        Binding("ctrl+up", "scroll_one('up')", "scroll one up", show=False),
        Binding("ctrl+down", "scroll_one('down')", "scroll one down", show=False),
        # Making selections (generally holding the shift key and moving cursor)
        Binding(
            "ctrl+shift+left",
            "cursor_word_left(True)",
            "cursor left word select",
            show=False,
        ),
        Binding(
            "ctrl+shift+right",
            "cursor_word_right(True)",
            "cursor right word select",
            show=False,
        ),
        Binding(
            "shift+home",
            "cursor_line_start(True)",
            "cursor line start select",
            show=False,
        ),
        Binding(
            "shift+end", "cursor_line_end(True)", "cursor line end select", show=False
        ),
        Binding(
            "ctrl+shift+home",
            "cursor_doc_start(True)",
            "select to cursor doc start",
            show=False,
        ),
        Binding(
            "ctrl+shift+end",
            "cursor_doc_end(True)",
            "select to cursor doc end",
            show=False,
        ),
        Binding("shift+up", "cursor_up(True)", "cursor up select", show=False),
        Binding("shift+down", "cursor_down(True)", "cursor down select", show=False),
        Binding("shift+left", "cursor_left(True)", "cursor left select", show=False),
        Binding("shift+right", "cursor_right(True)", "cursor right select", show=False),
        # Binding("f5", "select_word", "select word", show=False),
        # Binding("f6", "select_line", "select line", show=False),
        Binding("ctrl+a", "select_all", "select all", show=False),
        # Editing
        Binding("ctrl+underscore", "toggle_comment", "toggle comment", show=False),
        Binding("ctrl+x", "cut", "copy", show=False),
        Binding("ctrl+c", "copy", "copy", show=False),
        Binding("ctrl+u,ctrl+v,shift+insert", "paste", "paste", show=False),
        Binding("ctrl+z", "undo", "undo", show=False),
        Binding("ctrl+y", "redo", "redo", show=False),
        # Deletion
        Binding("backspace", "delete_left", "delete left", show=False),
        Binding("delete", "delete_right", "delete right", show=False),
        Binding("shift+delete", "delete_line", "delete line", show=False),
        # Binding(
        #     "ctrl+w", "delete_word_left", "delete left to start of word", show=False
        # ),
        # Binding(
        #     "ctrl+f", "delete_word_right", "delete right to start of word", show=False
        # ),
        # Binding(
        #     "ctrl+u", "delete_to_start_of_line", "delete to line start", show=False
        # ),
        # Binding("ctrl+k", "delete_to_end_of_line", "delete to line end", show=False),
    ]

    clipboard: str = ""
    completer_active: Literal["path", "member", "word"] | None = None

    class ShowCompletionList(Message):
        def __init__(self, prefix: str) -> None:
            super().__init__()
            self.prefix = prefix

        def __repr__(self) -> str:
            return f"ShowCompletionList({self.prefix=})"

        def __str__(self) -> str:
            return f"ShowCompletionList({self.prefix=})"

    class CompletionListKey(Message):
        def __init__(self, key: events.Key) -> None:
            super().__init__()
            self.key = key

    class ClipboardReady(Message):
        def __init__(
            self, copy: Callable[[Any], None], paste: Callable[[], str]
        ) -> None:
            super().__init__()
            self.copy = copy
            self.paste = paste

    def __init__(
        self,
        text: str = "",
        *,
        language: str | None = None,
        theme: str = "css",
        use_system_clipboard: bool = True,
        name: str | None = None,
        id: str | None = None,  # noqa: A002
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(
            text,
            language=language,
            theme=theme,
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
            soft_wrap=False,
            tab_behavior="indent",
            show_line_numbers=True,
        )
        self.cursor_blink = False if self.app.is_headless else True
        self.use_system_clipboard = use_system_clipboard
        self.double_click_location: Location | None = None
        self.double_click_timer: Timer | None = None
        self.consecutive_clicks: int = 0
        self.system_copy: Callable[[Any], None] | None = None
        self.system_paste: Callable[[], str] | None = None

    def on_mount(self) -> None:
        self._determine_clipboard()
        self.history.checkpoint()

    def on_blur(self, event: events.Blur) -> None:
        self.post_message(TextAreaHideCompletionList())

    def on_key(self, event: events.Key) -> None:
        # Naked shift or ctrl keys on Windows get sent as NUL chars; Textual
        # interprets these as `ctrl+@` presses, which is inconsistent with
        # other platforms. We ignore these presses.
        # https://github.com/Textualize/textual/issues/872
        if event.key == "ctrl+@":
            event.stop()
            event.prevent_default()
            return

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
            self._handle_quote_or_bracket(event)
        elif event.key == "enter":
            self._handle_enter(event)
        elif event.key == "tab":
            self._handle_tab(event)
        elif event.key == "shift+tab":
            self._handle_shift_tab(event)
        elif event.key in ("up", "down", "pageup", "pagedown"):
            self._handle_up_down(event)
        elif event.key == "backspace":
            self._handle_backspace(event)
        elif event.key in ("slash", "backslash"):
            self._handle_slash(event)
        elif event.key in ("full_stop", "colon"):
            self._handle_separator(event)
        elif event.key == "escape":
            self._handle_escape(event)
        elif event.character and event.is_printable:
            self._handle_printable_character(event)
        else:
            self.post_message(TextAreaHideCompletionList())

    def on_mouse_down(self, event: events.MouseDown) -> None:
        self.post_message(TextAreaHideCompletionList())
        target = self.get_target_document_location(event)
        if (
            self.double_click_location is not None
            and self.double_click_location == target
        ):
            event.prevent_default()
            self._selecting = True
            self.capture_mouse()
            self._pause_blink(visible=True)

    def on_mouse_up(self, event: events.MouseUp) -> None:
        target = self.get_target_document_location(event)
        if (
            self.consecutive_clicks > 0
            and self.double_click_location is not None
            and self.double_click_location == target
        ):
            if self.consecutive_clicks == 1:
                self.action_select_word()
            elif self.consecutive_clicks == 2:
                self.action_select_line()
                self.action_cursor_right(select=True)
            else:
                self.action_select_all()
            self.consecutive_clicks += 1
        else:
            self.history.checkpoint()
            self.double_click_location = target
            self.consecutive_clicks += 1

        if self.double_click_timer is not None:
            self.double_click_timer.reset()
        else:
            self.double_click_timer = self.set_timer(
                delay=0.5, callback=self._clear_double_click, name="double_click_timer"
            )

    def on_paste(self, event: Paste) -> None:
        event.prevent_default()
        event.stop()
        self.post_message(TextAreaHideCompletionList())
        self.history.checkpoint()
        self.replace(event.text, *self.selection, maintain_selection_offset=False)

    @on(ClipboardReady)
    def _set_clipboard(self, message: ClipboardReady) -> None:
        self.system_copy = message.copy
        self.system_paste = message.paste

    def watch_language(self, language: str) -> None:
        self.inline_comment_marker = INLINE_MARKERS.get(language)

    def replace_current_word(self, new_word: str) -> None:
        current_word = self._get_word_before_cursor()
        offset = len(current_word)
        self.replace(
            new_word,
            start=(self.cursor_location[0], self.cursor_location[1] - offset),
            end=self.cursor_location,
            maintain_selection_offset=False,
        )

    @work(thread=True)
    def _determine_clipboard(self) -> None:
        if self.use_system_clipboard:
            copy, paste = pyperclip.determine_clipboard()
            self.post_message(self.ClipboardReady(copy=copy, paste=paste))

    def action_copy(self) -> None:
        self._copy_selection()

    def action_cut(self) -> None:
        self.post_message(TextAreaHideCompletionList())
        self.history.checkpoint()
        self._copy_selection()
        if not self.selected_text:
            self.action_delete_line()
        self.delete(*self.selection)

    def action_cursor_doc_start(self, select: bool = False) -> None:
        self.post_message(TextAreaHideCompletionList())
        if select:
            self.selection = Selection(start=self.selection.start, end=(0, 0))
        else:
            self.selection = Selection(start=(0, 0), end=(0, 0))

    def action_cursor_doc_end(self, select: bool = False) -> None:
        self.post_message(TextAreaHideCompletionList())
        if select:
            self.selection = Selection(
                start=self.selection.start, end=self.document.end
            )
        else:
            self.selection = Selection(start=self.document.end, end=self.document.end)

    def action_delete_line(self) -> None:
        self.post_message(TextAreaHideCompletionList())
        self.history.checkpoint()
        if self.selection.start != self.cursor_location:  # selection active
            self.delete(*self.selection, maintain_selection_offset=False)
        else:
            line, col = self.cursor_location
            if self.document.line_count == 1:
                super().action_delete_line()
            elif self.cursor_at_last_line:
                eol = len(self.document[line - 1])
                self.replace(
                    "", start=(line - 1, eol), end=self.get_cursor_line_end_location()
                )
                self.cursor_location = (line - 1, eol)
            else:
                self.delete(start=(line, 0), end=(line + 1, 0))
                self.cursor_location = (line, 0)

    def action_paste(self) -> None:
        self.post_message(TextAreaHideCompletionList())
        if self.use_system_clipboard and self.system_paste is not None:
            try:
                self.clipboard = self.system_paste()
            except pyperclip.PyperclipException:
                # no system clipboard; common in CI runners. Use internal
                # clipboard state of self.clipboard
                self.post_message(TextAreaClipboardError(action="paste"))
        if self.clipboard:
            self.post_message(Paste(self.clipboard))

    def action_select_word(self) -> None:
        self.post_message(TextAreaHideCompletionList())
        prev = self._get_character_before_cursor()
        next_char = self._get_character_at_cursor()
        at_start_of_word = self._word_pattern.match(prev) is None
        at_end_of_word = self._word_pattern.match(next_char) is None
        if at_start_of_word and not at_end_of_word:
            self.action_cursor_word_right(select=True)
        elif at_end_of_word and not at_start_of_word:
            self.action_cursor_word_left(select=True)
            self.section = Selection(start=self.selection.end, end=self.selection.start)
        else:
            self.action_cursor_word_left(select=False)
            self.action_cursor_word_right(select=True)

    def action_scroll_one(self, direction: str = "down") -> None:
        self.post_message(TextAreaHideCompletionList())
        if direction == "down":
            self.scroll_relative(y=1, animate=False)
        elif direction == "up":
            self.scroll_relative(y=-1, animate=False)

    def action_toggle_comment(self) -> None:
        self.post_message(TextAreaHideCompletionList())
        if self.inline_comment_marker:
            self.history.checkpoint()
            lines, first, last = self._get_selected_lines()
            stripped_lines = [line.lstrip() for line in lines]
            indents = [len(line) - len(line.lstrip()) for line in lines]
            # if lines are already commented, remove them
            if lines and all(
                [
                    not line or line.startswith(self.inline_comment_marker)
                    for line in stripped_lines
                ]
            ):
                offsets = [
                    (
                        0
                        if not line
                        else (
                            2 if line[len(self.inline_comment_marker)].isspace() else 1
                        )
                    )
                    for line in stripped_lines
                ]
                for lno, indent, offset in zip(
                    range(first[0], last[0] + 1), indents, offsets
                ):
                    self.delete(
                        start=(lno, indent),
                        end=(lno, indent + offset),
                        maintain_selection_offset=True,
                    )
            # add comment tokens to all lines
            else:
                comment_indent = min(
                    [indent for indent, line in zip(indents, stripped_lines) if line]
                )
                insertion = f"{self.inline_comment_marker} "
                for lno, stripped_line in enumerate(stripped_lines, start=first[0]):
                    if stripped_line:
                        # insert one character at a time, to create a single undo-able
                        # batch of edits.
                        # See https://github.com/Textualize/textual/issues/4428
                        for i, char in enumerate(insertion):
                            self.insert(
                                char,
                                location=(lno, comment_indent + i),
                                maintain_selection_offset=True,
                            )

    def action_undo(self) -> None:
        self.post_message(TextAreaHideCompletionList())
        super().action_undo()

    def action_redo(self) -> None:
        self.post_message(TextAreaHideCompletionList())
        super().action_redo()

    def _clear_double_click(self) -> None:
        self.consecutive_clicks = 0
        self.double_click_location = None
        self.double_click_timer = None

    def _copy_selection(self) -> None:
        if self.selected_text:
            self.clipboard = self.selected_text
        else:
            whole_line = self.get_text_range(
                self.get_cursor_line_start_location(),
                self.get_cursor_line_end_location(),
            )
            self.clipboard = f"{whole_line}{self.document.newline}"
        if self.use_system_clipboard and self.system_copy is not None:
            try:
                self.system_copy(self.clipboard)
            except pyperclip.PyperclipException:
                # no system clipboard; common in CI runners
                self.post_message(TextAreaClipboardError(action="copy"))

    def _get_character_at_cursor(self) -> str:
        if self.cursor_at_end_of_line:
            return ""
        return self.get_text_range(
            start=self.cursor_location, end=self.get_cursor_right_location()
        )

    def _get_character_before_cursor(self) -> str:
        if self.cursor_at_start_of_line:
            return ""
        return self.get_text_range(
            start=self.get_cursor_left_location(), end=self.cursor_location
        )

    def _get_word_before_cursor(self, event: events.Key | None = None) -> str:
        lno = self.cursor_location[0]
        line = self.get_text_range(start=(lno, 0), end=self.cursor_location)

        if event is not None and event.key == "backspace":
            if len(line) > 1:
                search_string = line[:-1]
            else:
                search_string = ""
        elif event is not None and event.character is not None:
            search_string = f"{line}{event.character}"
        else:
            search_string = line

        if self.completer_active == "path":
            pattern = PATH_PROG
        elif self.completer_active == "member":
            pattern = MEMBER_PROG
        else:
            pattern = WORD_PROG

        match = pattern.match(search_string[::-1])
        if match:
            return match.group(0)[::-1]
        else:
            return ""

    def _handle_backspace(self, event: events.Key) -> None:
        if self.completer_active is not None:
            current_word = self._get_word_before_cursor(event)
            if current_word:
                self.post_message(self.ShowCompletionList(prefix=current_word))
            else:
                self.post_message(TextAreaHideCompletionList())

    def _handle_enter(self, event: events.Key) -> None:
        event.stop()
        event.prevent_default()
        if self.completer_active is not None:
            self.post_message(self.CompletionListKey(event))
            return
        nl = self.document.newline
        first, last = sorted([*self.selection])
        indent = self._get_indent_level_of_line(index=first[0])
        self.selection = Selection(start=first, end=first)
        char_before = self._get_character_before_cursor()
        if char_before in BRACKETS:
            if self.indent_type == "tabs":
                new_indent = indent + 1
                indent_char = "\t"
            else:
                new_indent = indent + self.indent_width - (indent % self.indent_width)
                indent_char = " "
            self.replace(f"{nl}{indent_char*new_indent}", first, last)
            char_at = self._get_character_at_cursor()
            if char_at == BRACKETS[char_before]:
                loc = self.selection
                self.insert(f"{nl}{indent * indent_char}")
                self.selection = loc
        else:
            indent_char = "\t" if self.indent_type == "tabs" else " "
            self.insert(f"{nl}{indent * indent_char}", location=self.cursor_location)

    def _handle_quote_or_bracket(self, event: events.Key) -> None:
        event.stop()
        event.prevent_default()
        if self.completer_active != "member":
            self.post_message(TextAreaHideCompletionList())
        else:
            prefix = self._get_word_before_cursor(event=event)
            self.post_message(self.ShowCompletionList(prefix=prefix))
        assert event.character is not None
        if self.selection.start == self.selection.end:
            self._insert_closed_character_at_cursor(event.character)
        elif event.key in (
            "right_parenthesis",
            "right_square_bracket",
            "right_curly_bracket",
        ):
            self.replace(event.character, *self.selection)
        else:
            self._insert_characters_around_selection(event.character)

    def _handle_shift_tab(self, event: events.Key) -> None:
        event.stop()
        event.prevent_default()
        if self.completer_active is not None:
            self.post_message(self.CompletionListKey(event))
            return
        self._indent_selection(kind="dedent")

    def _handle_separator(self, event: events.Key) -> None:
        event.stop()
        if self.completer_active != "path":
            self.completer_active = "member"
        prefix = self._get_word_before_cursor(event)
        self.post_message(self.ShowCompletionList(prefix=prefix))

    def _handle_escape(self, event: events.Key) -> None:
        """
        starting in textual 0.49, escape is handled by on_key instead of
        a binding, so we inherited behavior we don't want. Trap this event
        and hide the completion list.
        """
        event.stop()
        event.prevent_default()
        self.selection = Selection(self.selection.end, self.selection.end)
        self.post_message(TextAreaHideCompletionList())

    def _handle_slash(self, event: events.Key) -> None:
        event.stop()
        self.completer_active = "path"
        prefix = self._get_word_before_cursor(event)
        self.post_message(self.ShowCompletionList(prefix=prefix))

    def _handle_tab(self, event: events.Key) -> None:
        event.stop()
        event.prevent_default()
        if self.completer_active is not None:
            self.post_message(self.CompletionListKey(event))
            return
        first, last = sorted([*self.selection])
        # in some cases, selections are replaced with indent
        if first[0] == last[0] and (
            first[1] == last[1]
            or first[1] != 0
            or last[1] != len(self.document.get_line(last[0])) - 1
        ):
            indent_char = "\t" if self.indent_type == "tabs" else " "
            indent_width = 1 if self.indent_type == "tabs" else self.indent_width
            self.replace(
                f"{indent_char*(indent_width - first[1] % indent_width)}",
                first,
                last,
                maintain_selection_offset=False,
            )
        # usually, selected lines are prepended with four-ish spaces
        else:
            self._indent_selection(kind="indent")

    def _handle_up_down(self, event: events.Key) -> None:
        if self.completer_active is not None:
            event.stop()
            event.prevent_default()
            self.post_message(self.CompletionListKey(event))

    def _handle_printable_character(self, event: events.Key) -> None:
        assert event.character is not None, "Error! Printable key with no character."
        if self.completer_active is None:
            if WORD_PROG.match(event.character) is not None:
                self.completer_active = "word"
            else:
                return
        current_word = self._get_word_before_cursor(event)
        if current_word:
            self.post_message(self.ShowCompletionList(prefix=current_word))
        else:
            self.post_message(TextAreaHideCompletionList())

    def _indent_selection(self, kind: Literal["indent", "dedent"]) -> None:
        rounder, offset = (ceil, -1) if kind == "dedent" else (floor, 1)

        original_selection = self.selection
        lines, first, last = self._get_selected_lines()
        if kind == "dedent" and not lines:
            return

        indent_width = 1 if self.indent_type == "tabs" else self.indent_width
        indent_char = "\t" if self.indent_type == "tabs" else " " * self.indent_width
        raw_indents = [
            self._get_indent_level_of_line(lno) for lno in range(first[0], last[0] + 1)
        ]
        tab_stops = [rounder(space / indent_width) for space in raw_indents]

        new_lines = [
            f"{indent_char * max(0, indent+offset)}{line.lstrip()}"
            for line, indent in zip(lines, tab_stops)
        ]
        self.replace(
            self.document.newline.join(new_lines),
            start=(first[0], 0),
            end=(last[0], len(self.document.get_line(last[0]))),
        )

        change_at_start = (
            0
            if original_selection.start[1] == 0
            else len(new_lines[original_selection.start[0] - first[0]])
            - len(lines[original_selection.start[0] - first[0]])
        )
        change_at_cursor = (
            0
            if original_selection.end[1] == 0
            else len(new_lines[original_selection.end[0] - first[0]])
            - len(lines[original_selection.end[0] - first[0]])
        )
        self.selection = Selection(
            start=(
                original_selection.start[0],
                original_selection.start[1] + change_at_start,
            ),
            end=(
                original_selection.end[0],
                original_selection.end[1] + change_at_cursor,
            ),
        )

    def _insert_characters_around_selection(self, character: str) -> None:
        first = min(*self.selection)
        self.insert(character, location=first, maintain_selection_offset=True)
        first, last = sorted([*self.selection])
        self.insert(CLOSERS[character], location=last, maintain_selection_offset=False)
        self.selection = Selection(start=first, end=last)

    def _insert_closed_character_at_cursor(self, character: str) -> None:
        if self._get_character_at_cursor() == character:
            self.action_cursor_right()
        else:
            if (character in BRACKETS and self._should_complete_brackets()) or (
                character in CLOSERS and self._should_complete_quotes()
            ):
                self.insert(character, self.cursor_location)
                loc = self.selection
                self.insert(CLOSERS[character], self.cursor_location)
                self.selection = loc
            else:
                self.insert(character, self.cursor_location)

    def _should_complete_brackets(self) -> bool:
        if self.cursor_at_end_of_line:
            return True

        next_char = self._get_character_at_cursor()
        if not next_char or next_char.isspace():
            return True
        elif next_char in """>:,.="'""":
            return True

        return False

    def _should_complete_quotes(self) -> bool:
        next_char = self._get_character_at_cursor()
        prev_char = self._get_character_before_cursor()
        if (
            self.cursor_at_end_of_line or next_char.isspace() or next_char in ")>:,.="
        ) and (
            self.cursor_at_start_of_line
            or prev_char.isspace()
            or NON_WORD_CHAR_PROG.match(prev_char) is not None
        ):
            return True
        return False

    def _get_indent_level_of_line(self, index: int | None = None) -> int:
        if index is None:
            index = self.cursor_location[0]
        line = self.document.get_line(index)
        while line.isspace() and index > 0:
            index -= 1
            line = self.document.get_line(index)
        if line.isspace():
            return 0
        indent_char = "\t" if self.indent_type == "tabs" else " "
        indent_level = len(line) - len(line.lstrip(indent_char))
        return indent_level

    def _get_selected_lines(self) -> tuple[list[str], Location, Location]:
        [first, last] = sorted([self.selection.start, self.selection.end])
        lines = [self.document.get_line(i) for i in range(first[0], last[0] + 1)]
        return lines, first, last


class TextEditor(Widget, can_focus=True, can_focus_children=False):
    """
    A Widget that presents a feature-rich, multiline text editor interface.

    Attributes:
        text (str): The contents of the TextEditor
        language (str): Must be the short name of a Pygments lexer
            (https://pygments.org/docs/lexers/), e.g., "python", "sql", "as3".
        theme (str): Must be name of a Pygments style (https://pygments.org/styles/),
            e.g., "bw", "github-dark", "solarized-light".
        theme_colors (WidgetColors): The colors extracted from the theme.
    """

    DEFAULT_CSS = """
    #textarea__save_open_input_label {
        margin: 0 0 0 3;
    }
    .validation-error {
        color: $error;
        text-style: italic;
    }
    """

    BINDINGS = [
        Binding("ctrl+s", "save", "Save Query"),
        Binding("ctrl+o", "load", "Open Query"),
        Binding("ctrl+f", "find", "Find"),
        Binding("f3", "find(True)", "Find Next"),
        Binding("ctrl+g", "goto_line", "Go To Line"),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    theme: Reactive[str] = reactive("monokai")

    def __init__(
        self,
        *children: Widget,
        name: str | None = None,
        id: str | None = None,  # noqa: A002
        classes: str | None = None,
        disabled: bool = False,
        language: str | None = None,
        theme: str = "monokai",
        text: str = "",
        use_system_clipboard: bool = True,
        path_completer: (
            Callable[[str], Sequence[tuple[RenderableType, str]]] | None
        ) = path_completer,
        member_completer: (
            Callable[[str], Sequence[tuple[RenderableType, str]]] | None
        ) = None,
        word_completer: (
            Callable[[str], Sequence[tuple[RenderableType, str]]] | None
        ) = None,
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
        self._theme = theme
        self._initial_text = text
        self._find_history: list[str] = []
        self.theme_colors = WidgetColors.from_theme(theme)
        self.use_system_clipboard = use_system_clipboard
        self.path_completer = path_completer
        self.member_completer = member_completer
        self.word_completer = word_completer

    @property
    def text(self) -> str:
        """
        Returns:
            (str) The contents of the TextEditor.
        """
        return self.text_input.text

    @text.setter
    def text(self, contents: str) -> None:
        """
        Args:
            contents (str): A string (optionally containing newlines) to
                set the contents of the TextEditor equal to.
        """
        self.text_input.history.checkpoint()
        self.text_input.replace(
            contents,
            start=(0, 0),
            end=self.text_input.document.end,
            maintain_selection_offset=False,
        )
        self.text_input.move_cursor((0, 0))

    @property
    def selected_text(self) -> str:
        """
        Returns:
            str: The contents of the TextEditor between the selection
            anchor and the cursor. Returns an empty string if the
            selection anchor is not set.
        """
        return self.text_input.selected_text

    @property
    def selection(self) -> Selection:
        """
        Returns
            Selection: The location of the cursor in the TextEditor
        """
        return self.text_input.selection

    @selection.setter
    def selection(self, selection: Selection) -> None:
        """
        Args:
            selection (Selection): The position (line number, pos)
            to move the cursor and selection anchor to
        """
        self.text_input.selection = selection

    @property
    def language(self) -> str | None:
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

    @property
    def line_count(self) -> int:
        """
        Returns the number of lines in the document.
        """
        return self.text_input.document.line_count

    def get_line(self, index: int) -> str:
        """
        Returns the line with the given index from the document.

        Args:
            index: The index of the line in the document.

        Returns:
            The str instance representing the line.
        """
        return self.text_input.document.get_line(index=index)

    def get_text_range(self, selection: Selection) -> str:
        """
        Get the text between a start and end location.

        Args:
            selection: The start and end locations

        Returns:
            The text between start and end.
        """
        return self.text_input.get_text_range(*selection)

    def insert_text_at_selection(self, text: str) -> None:
        """
        Inserts text at the current cursor position; if there is a selection anchor,
        first deletes the current selection.

        Args:
            text (str): The text to be inserted.
        """
        self.text_input.replace(
            text,
            *self.text_input.selection,
            maintain_selection_offset=False,
        )

    def copy_to_clipboard(self, text: str) -> None:
        """
        Sets the editor's internal clipboard, and the system clipboard if enabled, to
        the value of text

        Args:
            text (str): The text to place on the clipboard.
        """
        self.text_input.clipboard = text
        if self.use_system_clipboard and self.text_input.system_copy is not None:
            try:
                self.text_input.system_copy(text)
            except pyperclip.PyperclipException:
                self.post_message(TextAreaClipboardError(action="copy"))

    def pause_blink(self, visible: bool = True) -> None:
        """
        Pauses the blink of the cursor
        """
        self.text_input._pause_blink(visible=visible)

    def restart_blink(self) -> None:
        """
        Restarts the blink of the cursor
        """
        self.text_input._restart_blink()

    def prepare_query(self, source: str) -> "Query" | None:
        """
        Build a Query from source. The Query can be used with self.query_syntax_tree

        Args:
            source (str): A tree-sitter query. See
            https://tree-sitter.github.io/tree-sitter/using-parsers#query-syntax
        """
        return self.text_input.document.prepare_query(query=source)

    def query_syntax_tree(
        self,
        query: "Query",
        start_point: tuple[int, int] | None = None,
        end_point: tuple[int, int] | None = None,
    ) -> list[tuple["Node", str]]:
        """
        Query the tree-sitter syntax tree.

        Args:
            query (Query): The tree-sitter Query to perform.
            start_point (tuple[int, int] | None): The (row, column byte) to start the
                query at.
            end_point (tuple[int, int] | None): The (row, column byte) to end the
                query at.

        Returns:
            A tuple containing the nodes and text captured by the query.
        """
        return self.text_input.document.query_syntax_tree(
            query=query, start_point=start_point, end_point=end_point
        )

    @property
    def syntax_tree(self) -> "Tree" | None:
        """
        Returns the document's syntax tree.
        """
        if isinstance(self.text_input.document, SyntaxAwareDocument):
            return self.text_input.document._syntax_tree
        else:
            return None

    @property
    def parser(self) -> "Parser" | None:
        if isinstance(self.text_input.document, SyntaxAwareDocument):
            return self.text_input.document._parser
        else:
            return None

    def compose(self) -> ComposeResult:
        self.text_container = TextContainer()
        self.text_input = TextAreaPlus(language=self._language, text=self._initial_text)
        self.completion_list = CompletionList()
        self.footer = FooterContainer(classes="hide")
        self.footer_label = Label("", id="textarea__save_open_input_label")
        with self.text_container:
            yield self.text_input
            yield self.completion_list
        with self.footer:
            yield self.footer_label

    def on_mount(self) -> None:
        self.styles.background = self.theme_colors.bgcolor
        self.theme = self._theme

    def on_focus(self) -> None:
        self.text_input.focus()

    def on_click(self) -> None:
        self.text_input.focus()

    @on(TextAreaHideCompletionList)
    def hide_completion_list(self, event: TextAreaHideCompletionList) -> None:
        event.stop()
        self.completion_list.is_open = False
        self.text_input.completer_active = None

    @on(TextAreaPlus.SelectionChanged)
    def update_completion_list_offset(
        self, event: TextAreaPlus.SelectionChanged
    ) -> None:
        region_x, region_y, _, _ = self.text_input.region
        self.completion_list.cursor_offset = self.text_input.cursor_screen_offset - (
            region_x,
            region_y,
        )

    @on(TextAreaPlus.Changed)
    def check_for_find_updates(self) -> None:
        try:
            find_input = self.footer.query_one(FindInput)
        except Exception:
            return
        self._update_find_label(value=find_input.value)

    @on(TextAreaPlus.ShowCompletionList)
    def update_completers_and_completion_list_offset(
        self, event: TextAreaPlus.ShowCompletionList
    ) -> None:
        event.stop()
        region_x, region_y, _, _ = self.text_input.region
        self.completion_list.cursor_offset = self.text_input.cursor_screen_offset - (
            region_x,
            region_y,
        )
        if self.text_input.completer_active == "path":
            self.completion_list.show_completions(event.prefix, self.path_completer)
        elif self.text_input.completer_active == "member":
            self.completion_list.show_completions(event.prefix, self.member_completer)
        elif self.text_input.completer_active == "word":
            self.completion_list.show_completions(event.prefix, self.word_completer)

    @on(TextAreaPlus.CompletionListKey)
    def forward_keypress_to_completion_list(
        self, event: TextAreaPlus.CompletionListKey
    ) -> None:
        event.stop()
        self.completion_list.process_keypress(event.key)

    @on(OptionList.OptionSelected)
    def insert_completion(self, event: OptionList.OptionSelected) -> None:
        event.stop()
        value = getattr(event.option, "value", None) or str(event.option.prompt)
        self.text_input.replace_current_word(value)
        self.completion_list.is_open = False
        self.text_input.completer_active = None

    @on(CancellableInput.Cancelled)
    def clear_footer(self) -> None:
        self._clear_footer_input()
        self.text_input.focus()

    @on(Input.Changed)
    def update_validation_label(self, message: Input.Changed) -> None:
        if message.input.id is None:
            return
        label = self.footer_label
        if message.input.id in (
            "textarea__save_input",
            "textarea__open_input",
            "textarea__gotoline_input",
        ):
            message.stop()
            if message.validation_result and not message.validation_result.is_valid:
                label.add_class("validation-error")
                label.update(";".join(message.validation_result.failure_descriptions))
            elif (
                message.validation_result
                and message.validation_result.is_valid
                and message.input.id in ("textarea__save_input", "textarea__open_input")
            ):
                action = "Saving to" if "save" in message.input.id else "Opening"
                p = Path(message.input.value).expanduser().resolve()
                with suppress(ValueError):
                    p = Path("~") / p.relative_to(Path.home())
                label.remove_class("validation-error")
                label.update(f"{action} {p}")
            else:
                label.remove_class("validation-error")
                label.update("")
        elif message.input.id in ("textarea__find_input"):
            message.stop()
            self._find_next_after_cursor(value=message.value)

    @on(Input.Submitted, "#textarea__save_input")
    def save_file(self, message: Input.Submitted) -> None:
        """
        Handle the submit event for the Save and Open modals.
        """
        message.stop()
        expanded_path = Path(message.input.value).expanduser()
        try:
            expanded_path.parent.mkdir(parents=True, exist_ok=True)
            with open(expanded_path, "w") as f:
                f.write(self.text)
        except OSError as e:
            self.app.push_screen(
                ErrorModal(
                    title="Save File Error",
                    header=("There was an error when attempting to save your file:"),
                    error=e,
                )
            )
        else:
            self.post_message(TextAreaSaved(path=expanded_path))
        self._clear_footer_input()
        self.text_input.focus()

    @on(Input.Submitted, "#textarea__open_input")
    def open_file(self, message: Input.Submitted) -> None:
        message.stop()
        expanded_path = Path(message.input.value).expanduser()
        try:
            with open(expanded_path, "r") as f:
                contents = f.read()
        except OSError as e:
            self.app.push_screen(
                ErrorModal(
                    title="Open File Error",
                    header=("There was an error when attempting to open your file:"),
                    error=e,
                )
            )
        else:
            self.text = contents
        self._clear_footer_input()
        self.text_input.focus()

    @on(Input.Submitted, "#textarea__gotoline_input")
    def goto_line(self, message: Input.Submitted) -> None:
        message.stop()
        try:
            new_line = int(message.value) - 1
        except (ValueError, TypeError):
            return
        self.text_input.move_cursor((new_line, 0), select=False)
        self._clear_footer_input()
        self.text_input.focus()

    @on(Input.Submitted, "#textarea__find_input")
    def find_next(self, message: Input.Submitted) -> None:
        message.stop()
        message.input.checkpoint()  # type: ignore
        self.selection = Selection(start=self.selection.end, end=self.selection.end)
        self._find_next_after_cursor(value=message.value)

    def watch_theme(self, theme: str) -> None:
        try:
            ti = self.text_input
        except AttributeError:
            return
        if theme in ti.available_themes:
            ti.theme = theme
        else:
            textarea_theme = text_area_theme_from_pygments_name(theme)
            ti.register_theme(textarea_theme)
            ti.theme = textarea_theme.name
        self.theme_colors = WidgetColors.from_theme(theme)

    def action_save(self) -> None:
        self._clear_footer_input()
        self._mount_footer_path_input("save")

    def action_load(self) -> None:
        self._clear_footer_input()
        self._mount_footer_path_input("open")

    def action_find(self, prepopulate_from_history: bool = False) -> None:
        try:
            find_input = self.footer.query_one(FindInput)
        except Exception:
            pass
        else:
            find_input.focus()
            return
        self._clear_footer_input()
        if prepopulate_from_history and self._find_history:
            value = self._find_history[-1]
        else:
            value = ""
        find_input = FindInput(value=value, history=self._find_history)
        self._mount_footer_input(input_widget=find_input)

    def action_goto_line(self) -> None:
        self._clear_footer_input()
        goto_input = GotoLineInput(
            max_line_number=self.text_input.document.line_count,
            current_line=self.selection.end[0] + 1,
            min_line_number=1,
            id="textarea__gotoline_input",
        )
        self._mount_footer_input(input_widget=goto_input)

    def _clear_footer_input(self) -> None:
        try:
            self.footer.query_one(Input).remove()
        except Exception:
            pass
        try:
            self.footer_label.update("")
        except Exception:
            pass
        self.footer.add_class("hide")

    def _mount_footer_input(self, input_widget: Input) -> None:
        input_widget.styles.background = self.theme_colors.bgcolor
        input_widget.styles.border = "round", self.theme_colors.contrast_text_color
        input_widget.styles.color = self.theme_colors.contrast_text_color
        self.footer.remove_class("hide")
        self.footer.mount(input_widget)
        input_widget.focus()

    def _mount_footer_path_input(self, name: str) -> None:
        if name == "open":
            file_okay, dir_okay, must_exist = True, False, True
        else:
            file_okay, dir_okay, must_exist = True, False, False

        path_input = PathInput(
            id=f"textarea__{name}_input",
            placeholder=f"{name.capitalize()}: Enter file path OR press ESC to cancel",
            file_okay=file_okay,
            dir_okay=dir_okay,
            must_exist=must_exist,
        )
        self._mount_footer_input(input_widget=path_input)

    def _find_next_after_cursor(self, value: str) -> None:
        label = self.footer_label
        if not value:
            label.update("")
            return
        cursor = self.selection.start
        lines = self.text_input.document.lines
        # first search text after the cursor
        for i, line in enumerate(lines[cursor[0] :]):
            pos = line.find(value, cursor[1] if i == 0 else None)
            if pos >= 0:
                self.selection = Selection(
                    start=(cursor[0] + i, pos),
                    end=(cursor[0] + i, pos + cell_len(value)),
                )
                break
        # search text from beginning, including line with cursor
        else:
            for i, line in enumerate(lines[: cursor[0] + 1]):
                pos = line.find(value)
                if pos >= 0:
                    self.selection = Selection(
                        start=(i, pos), end=(i, pos + cell_len(value))
                    )
                    break
        self.text_input.scroll_cursor_visible(animate=True)
        self._update_find_label(value=value)

    def _update_find_label(self, value: str) -> None:
        label = self.footer_label
        n_matches = self.text.count(value)
        if n_matches > 1:
            label.update(f"{n_matches} found; Enter for next; ESC to close")
        elif n_matches > 0:
            label.update(f"{n_matches} found")
        else:
            label.update("No results.")
