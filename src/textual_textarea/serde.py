from typing import List


def serialize_lines(lines: List[str]) -> str:
    return "\n".join([line.rstrip() for line in lines])


def deserialize_lines(text: str, trim: bool = False) -> List[str]:
    if text:
        lines = [f"{line} " for line in text.splitlines()]
        if text.endswith(("\n", "\r", "\r\n")):
            lines.append(" ")
    else:
        lines = [" "]

    if trim:
        lines[-1] = lines[-1].rstrip()

    return lines
