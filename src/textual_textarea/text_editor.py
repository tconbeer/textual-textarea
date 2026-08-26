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
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Input, Label, OptionList, TextArea
from textual.widgets.text_area import Location, Selection, SyntaxAwareDocument

from textual_textarea.autocomplete import CompletionList
from textual_textarea.cancellable_input import CancellableInput
from textual_textarea.colors import text_area_theme_from_app_theme
from textual_textarea.comments import INLINE_MARKERS
from textual_textarea.completion_scopes import (
    COMMENT_NODES,
    INTERPOLATION_NODES,
    STRING_NODES,
    is_string,
    scan_for_unterminated_scope,
)
from textual_textarea.containers import FooterContainer, TextContainer
from textual_textarea.error_modal import ErrorModal
from textual_textarea.find_input import FindInput
from textual_textarea.goto_input import GotoLineInput
from textual_textarea.messages import (
    TextAreaClipboardError,
    TextAreaHideCompletionList,
    TextAreaSaved,
    TextAreaThemeError,
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

        /* TextArea shades the cursor's line and gutter with $boost. Through
        Textual 6, $boost was the contrast text at 4% alpha; since Textual 7 it
        is only computed for themes that leave `panel` unset, so it is fully
        transparent for every built-in theme but textual-dark, and the shading
        disappears. Restore it with the value $boost used to have. */
        &:dark {
            & .text-area--cursor-line {
                background: white 4%;
            }
            & .text-area--cursor-gutter {
                background: white 4%;
            }
        }

        &:light {
            & .text-area--cursor-line {
                background: black 4%;
            }
            & .text-area--cursor-gutter {
                background: black 4%;
            }
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
        Binding("ctrl+a", "select_all", "select all", show=False),
        # Editing. The super+ aliases are the cmd key on macOS; Textual reports
        # them on terminals that support the Kitty keyboard protocol.
        Binding("ctrl+underscore", "toggle_comment", "toggle comment", show=False),
        Binding("ctrl+x,super+x", "cut", "cut", show=False),
        Binding("ctrl+c,super+c", "copy", "copy", show=False),
        Binding("ctrl+u,ctrl+v,super+v,shift+insert", "paste", "paste", show=False),
        Binding("ctrl+z,super+z", "undo", "undo", show=False),
        Binding("ctrl+y,super+y", "redo", "redo", show=False),
        # Deletion
        Binding("backspace", "delete_left", "delete left", show=False),
        Binding("delete", "delete_right", "delete right", show=False),
        Binding("shift+delete", "delete_line", "delete line", show=False),
        Binding(
            "ctrl+backspace,alt+backspace",
            "delete_word_left",
            "delete left to start of word",
            show=False,
        ),
        Binding(
            "alt+delete",
            "delete_word_right",
            "delete right to start of word",
            show=False,
        ),
    ]

    clipboard: str = ""
    completer_active: Literal["path", "member", "word"] | None = None
    suppress_completion_in_comments: bool = True
    suppress_completion_in_strings: bool = True

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
        read_only: bool = False,
        suppress_completion_in_comments: bool = True,
        suppress_completion_in_strings: bool = True,
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
            read_only=read_only,
        )
        self.cursor_blink = False if self.app.is_headless else True
        self.suppress_completion_in_comments = suppress_completion_in_comments
        self.suppress_completion_in_strings = suppress_completion_in_strings
        self.use_system_clipboard = use_system_clipboard
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

    def on_click(self, event: events.Click) -> None:
        """
        Expand the selection for repeated clicks at the same location: a double
        click selects the word under the cursor, a triple click selects the line,
        and any further clicks select the whole document. Textual counts the
        clicks in the chain for us.
        """
        if event.chain == 1:
            return
        elif event.chain == 2:
            self.action_select_word()
        elif event.chain == 3:
            self.action_select_line()
            self.action_cursor_right(select=True)
        else:
            self.action_select_all()

    def on_paste(self, event: Paste) -> None:
        event.prevent_default()
        event.stop()
        self.post_message(TextAreaHideCompletionList())
        self.history.checkpoint()
        self.replace(event.text, *self.selection, maintain_selection_offset=False)
        # replace() scrolled the cursor into view on Textual 6.4, but stopped
        # doing so in 7.x, so pasting a long line left the cursor off-screen.
        self.scroll_cursor_visible()

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
        # see on_paste: replace() no longer scrolls the cursor into view.
        self.scroll_cursor_visible()

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
            except Exception:
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
                marker_offset = len(self.inline_comment_marker)
                offsets = [
                    (
                        0
                        if not line
                        else (
                            marker_offset + 1
                            if line[marker_offset].isspace()
                            else marker_offset
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

    def _copy_selection(self) -> None:
        if self.selected_text:
            self.clipboard = self.selected_text
        else:
            whole_line = self.get_text_range(
                self.get_cursor_line_start_location(),
                self.get_cursor_line_end_location(),
            )
            self.clipboard = f"{whole_line}{self.document.newline}"
        # Textual's own clipboard: sets App.clipboard and emits OSC 52, which
        # reaches the system clipboard over ssh and in terminals where pyperclip
        # has no backend.
        self.app.copy_to_clipboard(self.clipboard)
        if self.use_system_clipboard and self.system_copy is not None:
            try:
                self.system_copy(self.clipboard)
            except Exception:
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

    def _get_node_before_cursor(self) -> "Node" | None:
        """
        The innermost syntax tree node containing the character before the
        cursor, or None if the document isn't parsed or the cursor is at the
        start of it.

        The character before the cursor, not the one at it: the cursor sits at
        the end of the word being typed, and tree-sitter's point ranges are
        half-open, so a point at the cursor itself is already outside the node
        the word belongs to.
        """
        document = self.document
        if not isinstance(document, SyntaxAwareDocument):
            return None
        location = self.get_cursor_left_location()
        if location == self.cursor_location:
            return None
        row, column = location
        point = (row, len(document.get_line(row)[:column].encode("utf-8")))
        return document._syntax_tree.root_node.descendant_for_point_range(point, point)

    def _get_node_opening_characters(self, node: "Node", count: int = 8) -> str:
        """
        The first count characters of a node's text, read from the document so
        that a node spanning a large amount of text isn't copied on every
        keypress.
        """
        row, byte_column = node.start_point
        line = self.document.get_line(row).encode("utf-8")
        return line[byte_column : byte_column + count].decode("utf-8", errors="ignore")

    def _cursor_is_inside_node(
        self, node: "Node", unclosed_at_end_of_line: bool = False
    ) -> bool:
        """
        Whether the cursor is inside a node that contains the character before
        it, as opposed to sitting just past the node's end.

        The distinction matters at a closing delimiter: `"abc"` no longer
        encloses the cursor once it is past the closing quote, and completing a
        member of a string literal is a real thing to want. A comment that runs
        to the end of its line has no closing delimiter to get past, though, so
        callers pass unclosed_at_end_of_line for those. That does mean the
        first character typed directly after a block comment that ends a line
        gets no completions.
        """
        row, column = self.cursor_location
        cursor_point = (row, len(self.document.get_line(row)[:column].encode("utf-8")))
        if cursor_point < node.end_point:
            return True
        if not unclosed_at_end_of_line:
            return False
        end_row, end_byte_column = node.end_point
        return end_byte_column >= len(self.document.get_line(end_row).encode("utf-8"))

    def _cursor_is_in_no_completion_scope(self) -> bool:
        """
        Whether the cursor sits inside a comment or a string literal, where a
        word or member completion is noise -- and, since the completion list
        preselects its first option, destructive on enter.
        """
        language = self.language
        if language is None:
            return False
        comment_nodes = (
            COMMENT_NODES.get(language, ())
            if self.suppress_completion_in_comments
            else ()
        )
        string_nodes = (
            STRING_NODES.get(language, ())
            if self.suppress_completion_in_strings
            else ()
        )
        if not comment_nodes and not string_nodes:
            return False

        interpolation_nodes = INTERPOLATION_NODES.get(language, ())
        node = self._get_node_before_cursor()
        while node is not None:
            if node.type in interpolation_nodes:
                # an f-string's braces (or a template literal's ${}) contain
                # code, not string content.
                return False
            if node.type in comment_nodes and self._cursor_is_inside_node(
                node, unclosed_at_end_of_line=True
            ):
                return True
            if (
                node.type in string_nodes
                and is_string(language, self._get_node_opening_characters(node))
                and self._cursor_is_inside_node(node)
            ):
                return True
            node = node.parent

        if self._syntax_tree_has_error():
            # an unterminated string or block comment doesn't parse to a node
            # of its own type, so fall back to scanning the line whenever the
            # tree has an error.
            row, column = self.cursor_location
            scope = scan_for_unterminated_scope(
                language, self.document.get_line(row)[:column]
            )
            if scope == "comment":
                return bool(comment_nodes)
            if scope == "string":
                return bool(string_nodes)
        return False

    def _syntax_tree_has_error(self) -> bool:
        document = self.document
        if not isinstance(document, SyntaxAwareDocument):
            return False
        return bool(document._syntax_tree.root_node.has_error)

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
        if self.read_only:
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
            self.replace(f"{nl}{indent_char * new_indent}", first, last)
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
        if self.read_only:
            return
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
        if self.read_only:
            self.app.action_focus_previous()
            return
        if self.completer_active is not None:
            self.post_message(self.CompletionListKey(event))
            return
        self._indent_selection(kind="dedent")

    def _handle_separator(self, event: events.Key) -> None:
        event.stop()
        if self.completer_active != "path":
            if self._cursor_is_in_no_completion_scope():
                self.post_message(TextAreaHideCompletionList())
                return
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
        if self.read_only:
            self.app.action_focus_next()
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
                f"{indent_char * (indent_width - first[1] % indent_width)}",
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
            if WORD_PROG.match(event.character) is None:
                return
            if self._cursor_is_in_no_completion_scope():
                self.post_message(TextAreaHideCompletionList())
                return
            self.completer_active = "word"
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
            f"{indent_char * max(0, indent + offset)}{line.lstrip()}"
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
    """

    DEFAULT_CSS = """
    #textarea__save_open_input_label {
        margin: 0 0 0 3;
    }
    .validation-error {
        color: $error;
        text-style: italic;
    }
    Input.textarea--footer-input {
        border: round $foreground;
        color: $foreground;
        background: $background;
        &.-invalid {
            border: round $error 60%;
        }
        &.-invalid:focus {
            border: round $error;
        }  
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

    theme: reactive[str] = reactive("monokai")

    def __init__(
        self,
        *children: Widget,
        name: str | None = None,
        id: str | None = None,  # noqa: A002
        classes: str | None = None,
        disabled: bool = False,
        read_only: bool = False,
        language: str | None = None,
        theme: str = "css",
        text: str = "",
        use_system_clipboard: bool = True,
        suppress_completion_in_comments: bool = True,
        suppress_completion_in_strings: bool = True,
        path_completer: (
            Callable[
                [str],
                Sequence[tuple[RenderableType, str]]
                | Sequence[tuple[tuple[str, str], str]],
            ]
            | None
        ) = path_completer,
        member_completer: (
            Callable[
                [str],
                Sequence[tuple[RenderableType, str]]
                | Sequence[tuple[tuple[str, str], str]],
            ]
            | None
        ) = None,
        word_completer: (
            Callable[
                [str],
                Sequence[tuple[RenderableType, str]]
                | Sequence[tuple[tuple[str, str], str]],
            ]
            | None
        ) = None,
    ) -> None:
        """
        Initializes an instance of a TextArea.

        Args:
            (see also textual.widget.Widget)
            language (str): Must be the short name of a tree-sitter language,
                e.g., "python", "sql"
            theme (str): Must be name of a Textual Theme.
            suppress_completion_in_comments (bool): Set to False to offer word
                and member completions inside comments.
            suppress_completion_in_strings (bool): Set to False to offer word
                and member completions inside string literals. The path
                completer is unaffected either way: completing a path inside a
                string is the whole point of it.
        """
        super().__init__(
            *children,
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
        )
        self._language = language
        self._theme = theme
        self._initial_text = text
        self._suppress_completion_in_comments = suppress_completion_in_comments
        self._suppress_completion_in_strings = suppress_completion_in_strings
        self._find_history: list[str] = []
        self.use_system_clipboard = use_system_clipboard
        self.text_input: TextAreaPlus | None = None
        self.read_only = read_only
        self.path_completer = path_completer
        self.member_completer = member_completer
        self.word_completer = word_completer

    @property
    def text(self) -> str:
        """
        Returns:
            (str) The contents of the TextEditor.
        """
        if self.text_input is None:
            return ""
        return self.text_input.text

    @text.setter
    def text(self, contents: str) -> None:
        """
        Args:
            contents (str): A string (optionally containing newlines) to
                set the contents of the TextEditor equal to.
        """
        if self.text_input is None:
            return
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
        if self.text_input is None:
            return ""
        return self.text_input.selected_text

    @property
    def selection(self) -> Selection:
        """
        Returns
            Selection: The location of the cursor in the TextEditor
        """
        if self.text_input is None:
            return Selection((0, 0), (0, 0))
        return self.text_input.selection

    @selection.setter
    def selection(self, selection: Selection) -> None:
        """
        Args:
            selection (Selection): The position (line number, pos)
            to move the cursor and selection anchor to
        """
        if self.text_input is None:
            return
        self.text_input.selection = selection

    @property
    def language(self) -> str | None:
        """
        Returns
            str | None: The tree-sitter short name of the active language
        """
        if self.text_input is None:
            return None
        return self.text_input.language

    @language.setter
    def language(self, language: str) -> None:
        """
        Args:
            langage (str | None): The Pygments short name for the new language
        """
        if self.text_input is None:
            return None
        self.text_input.language = language

    @property
    def suppress_completion_in_comments(self) -> bool:
        """
        Returns:
            bool: Whether the word and member completers stay closed inside a
            comment.
        """
        return self._suppress_completion_in_comments

    @suppress_completion_in_comments.setter
    def suppress_completion_in_comments(self, suppress: bool) -> None:
        self._suppress_completion_in_comments = suppress
        if self.text_input is not None:
            self.text_input.suppress_completion_in_comments = suppress

    @property
    def suppress_completion_in_strings(self) -> bool:
        """
        Returns:
            bool: Whether the word and member completers stay closed inside a
            string literal. The path completer is unaffected either way.
        """
        return self._suppress_completion_in_strings

    @suppress_completion_in_strings.setter
    def suppress_completion_in_strings(self, suppress: bool) -> None:
        self._suppress_completion_in_strings = suppress
        if self.text_input is not None:
            self.text_input.suppress_completion_in_strings = suppress

    @property
    def line_count(self) -> int:
        """
        Returns the number of lines in the document.
        """
        if self.text_input is None:
            return 0
        return self.text_input.document.line_count

    def get_line(self, index: int) -> str:
        """
        Returns the line with the given index from the document.

        Args:
            index: The index of the line in the document.

        Returns:
            The str instance representing the line.
        """
        if self.text_input is None:
            return ""
        return self.text_input.document.get_line(index=index)

    def get_text_range(self, selection: Selection) -> str:
        """
        Get the text between a start and end location.

        Args:
            selection: The start and end locations

        Returns:
            The text between start and end.
        """
        if self.text_input is None:
            return ""
        return self.text_input.get_text_range(*selection)

    def insert_text_at_selection(self, text: str) -> None:
        """
        Inserts text at the current cursor position; if there is a selection anchor,
        first deletes the current selection.

        Args:
            text (str): The text to be inserted.
        """
        if self.text_input is None:
            return
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
        if self.text_input is None:
            self.post_message(TextAreaClipboardError(action="copy"))
            return
        self.text_input.clipboard = text
        self.app.copy_to_clipboard(text)
        if self.use_system_clipboard and self.text_input.system_copy is not None:
            try:
                self.text_input.system_copy(text)
            except Exception:
                self.post_message(TextAreaClipboardError(action="copy"))

    def pause_blink(self, visible: bool = True) -> None:
        """
        Pauses the blink of the cursor
        """
        if self.text_input is None:
            return
        self.text_input._pause_blink(visible=visible)

    def restart_blink(self) -> None:
        """
        Restarts the blink of the cursor
        """
        if self.text_input is None:
            return
        self.text_input._restart_blink()

    def prepare_query(self, source: str) -> "Query" | None:
        """
        Build a Query from source. The Query can be used with self.query_syntax_tree

        Args:
            source (str): A tree-sitter query. See
            https://tree-sitter.github.io/tree-sitter/using-parsers#query-syntax
        """
        if self.text_input is None:
            return None
        return self.text_input.document.prepare_query(query=source)

    def query_syntax_tree(
        self,
        query: "Query",
        start_point: tuple[int, int] | None = None,
        end_point: tuple[int, int] | None = None,
    ) -> dict[str, list["Node"]]:
        """
        Query the tree-sitter syntax tree.

        Args:
            query (Query): The tree-sitter Query to perform.
            start_point (tuple[int, int] | None): The (row, column byte) to start the
                query at.
            end_point (tuple[int, int] | None): The (row, column byte) to end the
                query at.

        Returns:
            A dict mapping captured node names to lists of Nodes with that name
        """
        if self.text_input is None:
            return {}
        return self.text_input.document.query_syntax_tree(
            query=query, start_point=start_point, end_point=end_point
        )

    @property
    def syntax_tree(self) -> "Tree" | None:
        """
        Returns the document's syntax tree.
        """
        if self.text_input is None:
            return None
        if isinstance(self.text_input.document, SyntaxAwareDocument):
            return self.text_input.document._syntax_tree
        else:
            return None

    @property
    def parser(self) -> "Parser" | None:
        if self.text_input is None:
            return None
        if isinstance(self.text_input.document, SyntaxAwareDocument):
            return self.text_input.document._parser
        else:
            return None

    def compose(self) -> ComposeResult:
        self.text_container = TextContainer()
        self.text_input = TextAreaPlus(
            language=self._language,
            text=self._initial_text,
            read_only=self.read_only,
            suppress_completion_in_comments=self._suppress_completion_in_comments,
            suppress_completion_in_strings=self._suppress_completion_in_strings,
        )
        self.completion_list = CompletionList()
        self.footer = FooterContainer(classes="hide")
        self.footer_label = Label("", id="textarea__save_open_input_label")
        with self.text_container:
            yield self.text_input
            yield self.completion_list
        with self.footer:
            yield self.footer_label

    def on_mount(self) -> None:
        # delay setting the reactive until the widget mounts so we can be sure that
        # self.text_input exists so watch_theme can do its thing.
        self.theme = self._theme

    def focus(self, scroll_visible: bool = True) -> "TextEditor":
        """
        Focus the inner TextArea directly. Taking focus here first and then
        forwarding it in on_focus would blur the TextArea on every call, and a
        blur dismisses an open completion list.
        """
        if self.text_input is None:
            super().focus(scroll_visible)
        else:
            self.text_input.focus(scroll_visible)
        return self

    def on_focus(self) -> None:
        # focus can also arrive from the focus chain (e.g. tab), which does not
        # go through self.focus().
        if self.text_input is not None:
            self.text_input.focus()

    def on_click(self) -> None:
        if self.text_input is not None:
            self.text_input.focus()

    @on(TextAreaHideCompletionList)
    def hide_completion_list(self, event: TextAreaHideCompletionList) -> None:
        event.stop()
        assert self.text_input is not None
        self.completion_list.is_open = False
        self.text_input.completer_active = None

    @on(TextAreaPlus.SelectionChanged)
    def update_completion_list_offset(
        self, event: TextAreaPlus.SelectionChanged
    ) -> None:
        assert self.text_input is not None
        region_x, region_y, _, _ = self.text_input.region
        self.completion_list.cursor_offset = self.text_input.cursor_screen_offset - (
            region_x,
            region_y,
        )

    @on(TextAreaPlus.Changed)
    def check_for_find_updates(self, event: TextAreaPlus.Changed) -> None:
        find_input = self.footer.query_one_optional(FindInput)
        if find_input is None:
            return
        self._update_find_label(value=find_input.value)

    @on(TextAreaPlus.ShowCompletionList)
    def update_completers_and_completion_list_offset(
        self, event: TextAreaPlus.ShowCompletionList
    ) -> None:
        event.stop()
        assert self.text_input is not None
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
        assert self.text_input is not None
        value = getattr(event.option, "value", None) or str(event.option.prompt)
        self.text_input.replace_current_word(value)
        self.completion_list.is_open = False
        self.text_input.completer_active = None

    @on(CancellableInput.Cancelled)
    async def clear_footer(self) -> None:
        await self._clear_footer_input()

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
            self._update_find_label(value=message.value)
            self._find_next_after_cursor(value=message.value)

    @on(Input.Submitted, "#textarea__save_input")
    async def save_file(self, message: Input.Submitted) -> None:
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
        await self._clear_footer_input()

    @on(Input.Submitted, "#textarea__open_input")
    async def open_file(self, message: Input.Submitted) -> None:
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
        await self._clear_footer_input()

    @on(Input.Submitted, "#textarea__gotoline_input")
    async def goto_line(self, message: Input.Submitted) -> None:
        message.stop()
        assert self.text_input is not None
        try:
            new_line = int(message.value) - 1
        except (ValueError, TypeError):
            return
        self.text_input.move_cursor((new_line, 0), select=False)
        await self._clear_footer_input()

    @on(Input.Submitted, "#textarea__find_input")
    def find_next(self, message: Input.Submitted) -> None:
        message.stop()
        message.input.checkpoint()  # type: ignore
        self.selection = Selection(start=self.selection.end, end=self.selection.end)
        self._find_next_after_cursor(value=message.value)

    def watch_theme(self, theme: str) -> None:
        if self.text_input is None:
            self.app.notify(
                message=(
                    "Could not load the selected theme in the TextArea, because "
                    "it has not yet loaded. Please try again."
                ),
                severity="warning",
            )
            return

        if theme in self.text_input.available_themes:
            self.text_input.theme = theme
        else:
            css_vars = self.app.get_css_variables()
            theme_obj = self.app.get_theme(theme_name=theme)
            if theme_obj is None:
                self.post_message(TextAreaThemeError(theme=theme))
                return
            textarea_theme = text_area_theme_from_app_theme(theme, theme_obj, css_vars)
            self.text_input.register_theme(textarea_theme)
            self.text_input.theme = theme

    async def action_save(self) -> None:
        await self._mount_footer_path_input("save")

    async def action_load(self) -> None:
        await self._mount_footer_path_input("open")

    async def action_find(self, prepopulate_from_history: bool = False) -> None:
        existing_input = self.footer.query_one_optional(FindInput)
        if existing_input is not None:
            existing_input.focus()
            return
        if prepopulate_from_history and self._find_history:
            value = self._find_history[-1]
        else:
            value = ""
        find_input = FindInput(
            value=value,
            history=self._find_history,
            classes="textarea--footer-input",
        )
        await self._mount_footer_input(input_widget=find_input)

    async def action_goto_line(self) -> None:
        existing_input = self.footer.query_one_optional(GotoLineInput)
        if existing_input is not None:
            existing_input.focus()
            return
        goto_input = GotoLineInput(
            max_line_number=self.text_input.document.line_count
            if self.text_input is not None
            else 10000,
            current_line=self.selection.end[0] + 1,
            min_line_number=1,
            id="textarea__gotoline_input",
            classes="textarea--footer-input",
        )
        await self._mount_footer_input(input_widget=goto_input)

    async def _clear_footer_input(self) -> None:
        if self.footer.has_focus or self.footer.has_focus_within:
            # move focus to the main text area
            self.focus()
        await self.footer.remove_children(Input)
        self.footer_label.update("")
        self.footer.add_class("hide")

    async def _mount_footer_input(self, input_widget: Input) -> None:
        """
        Footer's first child is always the validation label. It may
        or may not have a second child, which is an input.
        """
        if len(self.footer.children) > 1:
            if self.footer.children[1].id == input_widget.id:
                self.footer.children[1].focus()
                return
            else:
                self.footer_label.update("")
                await self.footer.remove_children(Input)
        self.footer.remove_class("hide")
        await self.footer.mount(input_widget)
        input_widget.focus()

    async def _mount_footer_path_input(self, name: str) -> None:
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
            classes="textarea--footer-input",
        )
        await self._mount_footer_input(input_widget=path_input)

    def _find_next_after_cursor(self, value: str) -> None:
        assert self.text_input is not None
        if not value:
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

    def _update_find_label(self, value: str) -> None:
        label = self.footer_label
        if not value:
            label.remove_class("validation-error")
            label.update("")
            return

        n_matches = self.text.count(value)
        if n_matches > 1:
            label.remove_class("validation-error")
            label.update(f"{n_matches} found; Enter for next; ESC to close")
        elif n_matches > 0:
            label.remove_class("validation-error")
            label.update(f"{n_matches} found")
        else:
            label.add_class("validation-error")
            label.update("No results.")
