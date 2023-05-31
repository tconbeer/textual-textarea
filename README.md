# Textual Textarea

# Installation

```
pip install textual-textarea
```

# Usage

## Initializing the Widget

The TextArea is a Textual Widget. You can add it to a Textual
app using `compose` or `mount`:

```python
from textual_textarea import TextArea
from textual.app import App, ComposeResult

class TextApp(App, inherit_bindings=False):
    def compose(self) -> ComposeResult:
        yield TextArea(language="python", theme="solarized-dark")

    def on_mount(self) -> None:
        ta = self.query_one(TextArea)
        ta.focus()

app = TextApp()
app.run()
```

In addition to the standard Widget arguments, TextArea accepts two additional, optional arguments when initializing the widget:

- language: Must be `None` or the short name of a [Pygments lexer](https://pygments.org/docs/lexers/), e.g., `python`, `sql`, `as3`. Defaults to None.
- theme: Must be name of a [Pygments style](https://pygments.org/styles/), e.g., `bw`, `github-dark`, `solarized-light`. Defaults to `monokai`.

The TextArea supports many actions and key bindings. **For proper binding of `ctrl+c` to the COPY action,
you must initialize your App with `inherit_bindings=False`** (as shown above), so that `ctrl+c` does not quit the app. The TextArea implements `ctrl+q` as quit; you way wish to mimic that in your app so that other in-focus widgets use the same behavior.

## Interacting with the Widget

### Getting and Setting Text

The TextArea exposes a `text` property that contains the full text contained in the widget. You can retrieve or set the text by interacting with this property:

```python
ta = self.query_one(TextArea)
old_text = ta.text
ta.text = "New Text!\n\nMany Lines!"
```

### Getting Theme Colors

If you would like the rest of your app to match the colors from the TextArea's theme, they are exposed via the `theme_colors` property.

```python
ta = self.query_one(TextArea)
color = ta.theme_colors.contrast_text_color
bgcolor = ta.theme_colors.bgcolor
highlight = ta.theme_colors.selection_bgcolor
```

You cannot set these colors this way, however.