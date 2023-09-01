# textual-textarea CHANGELOG

All notable changes to this project will be documented in this file.

## [Unreleased]

## [0.5.4] - 2023-09-01

### Bug Fixes

-   <kbd>up</kbd>, <kbd>down</kbd>, <kbd>pageup</kbd>, and <kbd>pagedown</kbd> now better maintain the cursor's x-position when starting with an x-position that is longer than adjacent lines ([#94](https://github.com/tconbeer/textual-textarea/issues/94)).

## [0.5.3] - 2023-09-01

### Bug Fixes

-   Undo is smarter about cursor positions and selections; it no longer saves a new checkpoint for every cursor position. ([#86](https://github.com/tconbeer/textual-textarea/issues/86)).
-   Clicks within the container but outside text will still update the cursor ([#93](https://github.com/tconbeer/textual-textarea/issues/93)).
-   The cursor is now scrolled into position much faster.

## [0.5.2] - 2023-08-23

### Bug Fixes

-   TextArea now uses the highlight color from the Pygments Style to highlight selected text.

## [0.5.1] - 2023-08-23

### Bug Fixes

-   Fixes a crash caused by <kbd>shift+delete</kbd> on a buffer with only one line.

## [0.5.0] - 2023-08-22

### Features

-   Undo any input with <kbd>ctrl+z</kbd>; redo with <kbd>ctrl+y</kbd> ([#12](https://github.com/tconbeer/textual-textarea/issues/12)).
-   <kbd>shift+delete</kbd> now deletes the current line if there is no selection ([#77](https://github.com/tconbeer/textual-textarea/issues/77)). 

### Tests

-   Adds basic fuzzing of text and keyboard inputs ([#50](https://github.com/tconbeer/textual-textarea/issues/50))

## [0.4.2] - 2023-08-03

### Bug Fixes

-   No longer clears selection for more keystrokes (e.g,. <kbd>ctrl+j</kbd>)
-   Better-maintains selection and cursor position when bulk commenting or uncommenting with <kbd>ctrl+/</kbd>

## [0.4.1] - 2023-08-03

### Features

-   Adds a parameter to PathInput to allow <kbd>tab</kbd> to advance the focus.

## [0.4.0] - 2023-08-03

### Features

-   Adds a suggester to autocomplete paths for the save and open file inputs.
-   Adds a validator to validate paths for the save and open file inputs.
-   `textual-textarea` now requires `textual` >=0.27.0
-   Adds reactive properties to the textarea for `selection_anchor` position and 
    `selected_text`.

## [0.3.3] - 2023-07-28

### Features

-   The open and save file inputs now expand the user home directory (`~`).

### Bug Fixes

-   Selection should be better-maintained when pressing F-keys.

## [0.3.2] - 2023-07-14

### Bug Fixes

-   Improves support for pasting text with `ctrl+v` on all platforms. ([#53](https://github.com/tconbeer/textual-textarea/issues/53)).

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

[Unreleased]: https://github.com/tconbeer/textual-textarea/compare/0.5.4...HEAD

[0.5.4]: https://github.com/tconbeer/textual-textarea/compare/0.5.3...0.5.4

[0.5.3]: https://github.com/tconbeer/textual-textarea/compare/0.5.2...0.5.3

[0.5.2]: https://github.com/tconbeer/textual-textarea/compare/0.5.1...0.5.2

[0.5.1]: https://github.com/tconbeer/textual-textarea/compare/0.5.0...0.5.1

[0.5.0]: https://github.com/tconbeer/textual-textarea/compare/0.4.2...0.5.0

[0.4.2]: https://github.com/tconbeer/textual-textarea/compare/0.4.1...0.4.2

[0.4.1]: https://github.com/tconbeer/textual-textarea/compare/0.4.0...0.4.1

[0.4.0]: https://github.com/tconbeer/textual-textarea/compare/0.3.3...0.4.0

[0.3.3]: https://github.com/tconbeer/textual-textarea/compare/0.3.2...0.3.3

[0.3.2]: https://github.com/tconbeer/textual-textarea/compare/0.3.1...0.3.2

[0.3.1]: https://github.com/tconbeer/textual-textarea/compare/0.3.0...0.3.1

[0.3.0]: https://github.com/tconbeer/textual-textarea/compare/0.2.2...0.3.0

[0.2.2]: https://github.com/tconbeer/textual-textarea/compare/0.2.1...0.2.2

[0.2.1]: https://github.com/tconbeer/textual-textarea/compare/0.2.0...0.2.1

[0.2.0]: https://github.com/tconbeer/textual-textarea/compare/0.1.2...0.2.0

[0.1.2]: https://github.com/tconbeer/textual-textarea/compare/0.1.1...0.1.2

[0.1.1]: https://github.com/tconbeer/textual-textarea/compare/0.1.0...0.1.1

[0.1.0]: https://github.com/tconbeer/textual-textarea/compare/9832e9bbe1cd7a2ce9a4f09746eb1c2ddc8df842...0.1.0
