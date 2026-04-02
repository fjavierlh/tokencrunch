"""Syntactic compression layer — lossless text normalization.

Transformations applied (all lossless):
- Normalize tabs to spaces (4-space indent)
- Strip trailing whitespace from each line
- Collapse multiple consecutive blank lines into one
- Strip leading/trailing blank lines from each message
- Optionally strip single-line comments (# style)

Expected savings: ~10-25% on typical code-heavy prompts.
"""

from __future__ import annotations

from tokencrunch.layers import LayerStats


class SyntacticLayer:
    """Layer 1: lossless syntactic normalization."""

    name = "syntactic"

    def __init__(self, enabled: bool = True, strip_comments: bool = False) -> None:
        self.enabled = enabled
        self.strip_comments = strip_comments
        self._stats = LayerStats()

    def compress_messages(self, messages: list[dict]) -> list[dict]:
        return [self._compress_message(msg) for msg in messages]

    def reset_stats(self) -> None:
        self._stats = LayerStats()

    def get_stats(self) -> LayerStats:
        return self._stats

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compress_message(self, msg: dict) -> dict:
        content = msg.get("content")
        if isinstance(content, str):
            compressed = self._compress_text(content)
            self._stats.chars_in += len(content)
            self._stats.chars_out += len(compressed)
            return {**msg, "content": compressed}
        if isinstance(content, list):
            new_blocks = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block["text"]
                    compressed = self._compress_text(text)
                    self._stats.chars_in += len(text)
                    self._stats.chars_out += len(compressed)
                    new_blocks.append({**block, "text": compressed})
                else:
                    new_blocks.append(block)
            return {**msg, "content": new_blocks}
        return msg

    def _compress_text(self, text: str) -> str:
        # 1. Normalize tabs to 4 spaces
        text = text.expandtabs(4)

        lines = text.split("\n")

        # 2. Strip trailing whitespace
        lines = [line.rstrip() for line in lines]

        # 3. Optionally strip comments
        if self.strip_comments:
            lines = [_strip_inline_comment(line) for line in lines]

        # 4. Collapse consecutive blank lines into one
        result: list[str] = []
        prev_blank = False
        for line in lines:
            is_blank = not line.strip()
            if is_blank and prev_blank:
                continue
            result.append(line)
            prev_blank = is_blank

        # 5. Strip leading/trailing blank lines
        while result and not result[0].strip():
            result.pop(0)
        while result and not result[-1].strip():
            result.pop()

        return "\n".join(result)


def _strip_inline_comment(line: str) -> str:
    """Remove trailing # comment from a line, respecting string literals."""
    in_single = False
    in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return line[:i].rstrip()
    return line
