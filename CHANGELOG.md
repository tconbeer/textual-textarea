# textual-textarea CHANGELOG

All notable changes to this project will be documented in this file.

## [Unreleased]

### Features

-   Uses the system clipboard for copy and paste operations, unless initialized
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

[Unreleased]: https://github.com/tconbeer/textual-textarea/compare/0.1.2...HEAD

[0.1.2]: https://github.com/tconbeer/textual-textarea/compare/0.1.1...0.1.2

[0.1.1]: https://github.com/tconbeer/textual-textarea/compare/0.1.0...0.1.1

[0.1.0]: https://github.com/tconbeer/textual-textarea/compare/9832e9bbe1cd7a2ce9a4f09746eb1c2ddc8df842...0.1.0
