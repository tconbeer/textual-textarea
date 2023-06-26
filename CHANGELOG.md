# textual-textarea CHANGELOG

All notable changes to this project will be documented in this file.

## [Unreleased]

## [0.3.1] - 2023-06-26

### Bug Fixes

-   Fixes issue where text area was aggressively capturing mouse events and not responding to mouse up events,
    which would cause issues if your App had widgets other than the TextArea ([#42](https://github.com/tconbeer/textual-textarea/issues/42)).
-   Fixes an issue where <kbd>PageUp</kbd> could cause a crash ([#46](https://github.com/tconbeer/textual-textarea/issues/46)).

## [0.3.0] - 2023-06-19

-   Select text using click and drag ([#8](https://github.com/tconbeer/textual-textarea/issues/8)).
-   Comment characters inserted with <kbd>ctrl+/</kbd> are now based on the language that the
    TextArea is initialized with ([#24](https://github.com/tconbeer/textual-textarea/issues/24)).
-   TextArea exposes a `language` property for the currently-configured language.

## [0.2.2] - 2023-06-15

### Features

-   Adds a cursor attribute to TextArea to make it easier to get and set the TextInput's cursor position.
-   Adds 3 attributes to TextArea to make it easier to access the child widgets: `text_input`, `text_container`, and `footer`.

### Bug Fixes

-   Fixes a bug that was preventing the cursor from being scrolled into view.

## [0.2.1] - 2023-06-15

### Bug Fixes

-   Fixes a bug where the TextArea did not update or have focus after opening a file ([#28](https://github.com/tconbeer/textual-textarea/issues/28))
-   Fixes a bug where a missing space at the end of the buffer after opening a file could cause a crash

## [0.2.0] - 2023-06-14

### Features

-   Uses the system clipboard (if it exists) for copy and paste operations, unless initialized
    with `use_system_clipboard=False`.
-   Adds a sample app that can be run with `python -m textual_textarea`.

## [0.1.2] - 2023-06-01

-   Makes top-level TextArea widget focusable
-   Loosens textual dependency to >=0.21.0
-   Adds py.typed file

## [0.1.1] - 2023-06-01

-   Exports TextArea class under the main textual_textarea module.

## [0.1.0] - 2023-06-01

-   Initial release: TextArea is a feature-rich text area (multiline) input, with
    support for syntax highlighting, themes, keyboard navigation, copy-paste, file
    opening and saving, and more!

[Unreleased]: https://github.com/tconbeer/textual-textarea/compare/0.3.1...HEAD

[0.3.1]: https://github.com/tconbeer/textual-textarea/compare/0.3.0...0.3.1

[0.3.0]: https://github.com/tconbeer/textual-textarea/compare/0.2.2...0.3.0

[0.2.2]: https://github.com/tconbeer/textual-textarea/compare/0.2.1...0.2.2

[0.2.1]: https://github.com/tconbeer/textual-textarea/compare/0.2.0...0.2.1

[0.2.0]: https://github.com/tconbeer/textual-textarea/compare/0.1.2...0.2.0

[0.1.2]: https://github.com/tconbeer/textual-textarea/compare/0.1.1...0.1.2

[0.1.1]: https://github.com/tconbeer/textual-textarea/compare/0.1.0...0.1.1

[0.1.0]: https://github.com/tconbeer/textual-textarea/compare/9832e9bbe1cd7a2ce9a4f09746eb1c2ddc8df842...0.1.0
