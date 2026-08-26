"""
Per-language declarations of the places where the word and member completers
should stay closed.

A string literal is the one place a user reliably does not want an identifier
or keyword completion, and a comment is the same; because the completion list
preselects its first option, offering one there means pressing enter replaces
what was typed with a completion.

Each mapping is keyed by the tree-sitter language name. A language that appears
in neither ``COMMENT_NODES`` nor ``STRING_NODES`` never suppresses completion,
so an unconfigured language behaves exactly as it did before this module
existed.
"""

from __future__ import annotations

from string import ascii_letters

from textual_textarea.comments import INLINE_MARKERS

# Node types for comments. Every node type here is unambiguously a comment, so
# a cursor anywhere inside one suppresses completion.
COMMENT_NODES: dict[str, tuple[str, ...]] = {
    "bash": ("comment",),
    "css": ("comment",),
    "go": ("comment",),
    "html": ("comment",),
    "java": ("line_comment", "block_comment"),
    "javascript": ("comment",),
    "python": ("comment",),
    "rust": ("line_comment", "block_comment"),
    "sql": ("comment", "marginalia"),
    "toml": ("comment",),
    "xml": ("Comment",),
    "yaml": ("comment",),
}

# Node types that may be string literals. A node type is not always enough on
# its own: tree-sitter-sql parses 'abc', "my col", and 123 all to a `literal`
# node, and only the first of those is a string -- a double-quoted name is an
# identifier, and completing a member after it is exactly what a user wants. A
# node of one of these types therefore counts as a string only if it opens with
# one of the language's STRING_QUOTES.
#
# The document languages whose strings are the document's structure rather than
# prose (JSON's keys and values, HTML and XML attribute values) are left out:
# there, completing inside a string is the point.
STRING_NODES: dict[str, tuple[str, ...]] = {
    "bash": ("string", "raw_string"),
    "css": ("string_value",),
    "go": ("interpreted_string_literal", "raw_string_literal"),
    "java": ("string_literal",),
    "javascript": ("string", "template_string"),
    "python": ("string",),
    "rust": ("string_literal",),
    "sql": ("literal",),
    "toml": ("string",),
    "yaml": ("single_quote_scalar", "double_quote_scalar"),
}

# The characters that open a string literal in each language, used both to tell
# a string node from a quoted identifier and to scan for an unterminated string
# (see is_string and ends_inside_string below).
STRING_QUOTES: dict[str, tuple[str, ...]] = {
    "bash": ("'", '"'),
    "css": ("'", '"'),
    "go": ('"', "`"),
    "java": ('"',),
    "javascript": ("'", '"', "`"),
    "python": ("'", '"'),
    "rust": ('"',),
    # only the single quote: a lone $ is far more likely to be a Postgres
    # placeholder ($1) or part of an identifier than the start of a
    # dollar-quoted string, and ends_inside_string would read it as one.
    "sql": ("'",),
    "toml": ("'", '"'),
    "yaml": ("'", '"'),
}

# Node types for the parts of a string that are code, not string content: the
# braces of a Python f-string, the ${} of a JavaScript template literal. A
# cursor inside one of these is writing an expression, and completions there
# are as useful as they are anywhere else.
INTERPOLATION_NODES: dict[str, tuple[str, ...]] = {
    "javascript": ("template_substitution",),
    "python": ("interpolation",),
}

# The delimiters of a block comment, for the fallback scan below. A line
# comment's marker comes from comments.INLINE_MARKERS, which already carries
# one per language.
BLOCK_COMMENT_MARKERS: dict[str, tuple[str, str]] = {
    "css": ("/*", "*/"),
    "go": ("/*", "*/"),
    "html": ("<!--", "-->"),
    "java": ("/*", "*/"),
    "javascript": ("/*", "*/"),
    "rust": ("/*", "*/"),
    "sql": ("/*", "*/"),
    "xml": ("<!--", "-->"),
}

# Characters that can precede a string's opening quote as part of its literal:
# SQL's N'abc' and E'abc', Python's rb'abc', Rust's br#"abc"#.
_STRING_PREFIX_CHARS = f"{ascii_letters}&#"


def is_string(language: str, opening_characters: str) -> bool:
    """
    Whether a node of a STRING_NODES type is a string literal, given the first
    few characters of its text.

    Args:
        language (str): The tree-sitter language name.
        opening_characters (str): The start of the node's text; must be long
            enough to cover any string prefix and the quote that follows it.
    """
    quotes = STRING_QUOTES.get(language)
    if quotes is None:
        # the language declares string nodes but no quotes to disambiguate
        # them, so every node of a declared type is a string.
        return True
    return opening_characters.lstrip(_STRING_PREFIX_CHARS)[:1] in quotes


def scan_for_unterminated_scope(language: str, text: str) -> str | None:
    """
    Scan the text of a line up to the cursor and report the scope it leaves
    open at its end: "string", "comment", or None.

    An unterminated string or block comment doesn't parse to a node of its own
    type -- the grammar leaves ERROR nodes behind, or recovers by parsing the
    contents as an identifier -- so this backstops the syntax tree whenever the
    tree has an error. It is deliberately naive: it knows about backslash
    escapes and nothing else, and it starts at the beginning of the line, so a
    string or block comment opened on an earlier line is invisible to it.

    Args:
        language (str): The tree-sitter language name.
        text (str): The text to scan, the line before the cursor.
    """
    quotes = STRING_QUOTES.get(language, ())
    line_marker = INLINE_MARKERS.get(language)
    block_markers = BLOCK_COMMENT_MARKERS.get(language)
    open_quote: str | None = None
    escaped = False
    index = 0
    while index < len(text):
        char = text[index]
        index += 1
        if escaped:
            escaped = False
        elif open_quote is not None:
            if char == "\\":
                escaped = True
            elif char == open_quote:
                open_quote = None
        elif char in quotes:
            open_quote = char
        elif line_marker and text.startswith(line_marker, index - 1):
            return "comment"
        elif block_markers and text.startswith(block_markers[0], index - 1):
            end = text.find(block_markers[1], index - 1 + len(block_markers[0]))
            if end < 0:
                return "comment"
            index = end + len(block_markers[1])
    return "string" if open_quote is not None else None
