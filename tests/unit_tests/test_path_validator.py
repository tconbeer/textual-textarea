from pathlib import Path

import pytest
from textual_textarea.path_input import PathValidator


@pytest.mark.parametrize(
    "relpath,dir_okay,file_okay,must_exist,expected_result",
    [
        ("foo", True, True, True, True),
        ("foo", True, True, False, True),
        ("foo", True, False, True, True),
        ("foo", True, False, False, True),
        ("foo", False, True, True, False),
        ("foo", False, True, False, False),
        ("foo", False, False, True, False),
        ("foo", False, False, False, False),
        ("bar", True, True, True, True),
        ("bar", True, True, False, True),
        ("bar", True, False, True, True),
        ("bar", True, False, False, True),
        ("bar", False, True, True, False),
        ("bar", False, True, False, False),
        ("bar", False, False, True, False),
        ("bar", False, False, False, False),
        ("baz", True, True, True, False),
        ("baz", True, True, False, True),
        ("baz", True, False, True, False),
        ("baz", True, False, False, True),
        ("baz", False, True, True, False),
        ("baz", False, True, False, True),
        ("baz", False, False, True, False),
        ("baz", False, False, False, True),
        ("foo/baz.txt", True, True, True, True),
        ("foo/baz.txt", True, True, False, True),
        ("foo/baz.txt", True, False, True, False),
        ("foo/baz.txt", True, False, False, False),
        ("foo/baz.txt", False, True, True, True),
        ("foo/baz.txt", False, True, False, True),
        ("foo/baz.txt", False, False, True, False),
        ("foo/baz.txt", False, False, False, False),
    ],
)
def test_path_validator(
    data_dir: Path,
    relpath: str,
    dir_okay: bool,
    file_okay: bool,
    must_exist: bool,
    expected_result: bool,
) -> None:
    p = data_dir / "test_validator" / relpath
    validator = PathValidator(dir_okay, file_okay, must_exist)
    result = validator.validate(str(p))
    assert result.is_valid == expected_result
