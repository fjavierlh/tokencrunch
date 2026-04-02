"""Unit tests for SyntacticLayer — pure logic, no I/O."""

from __future__ import annotations

import pytest

from tokencrunch.layers import LayerStats
from tokencrunch.layers.syntactic import SyntacticLayer, _strip_inline_comment


# ---------------------------------------------------------------------------
# Text compression primitives
# ---------------------------------------------------------------------------

class TestTrailingWhitespace:
    def test_stripped_from_single_line(self):
        layer = SyntacticLayer()
        assert layer._compress_text("hello   ") == "hello"

    def test_stripped_from_each_line(self):
        layer = SyntacticLayer()
        assert layer._compress_text("foo   \nbar  ") == "foo\nbar"

    def test_no_change_when_clean(self):
        layer = SyntacticLayer()
        assert layer._compress_text("hello\nworld") == "hello\nworld"


class TestTabNormalization:
    def test_tab_replaced_by_four_spaces(self):
        layer = SyntacticLayer()
        result = layer._compress_text("\thello")
        assert result == "    hello"

    def test_mixed_indent_normalized(self):
        layer = SyntacticLayer()
        result = layer._compress_text("\t\thello")
        assert result == "        hello"


class TestBlankLineCollapse:
    def test_two_blanks_become_one(self):
        layer = SyntacticLayer()
        assert layer._compress_text("a\n\n\nb") == "a\n\nb"

    def test_many_blanks_become_one(self):
        layer = SyntacticLayer()
        assert layer._compress_text("a\n\n\n\n\nb") == "a\n\nb"

    def test_single_blank_preserved(self):
        layer = SyntacticLayer()
        assert layer._compress_text("a\n\nb") == "a\n\nb"

    def test_leading_blank_lines_stripped(self):
        layer = SyntacticLayer()
        assert layer._compress_text("\n\nhello") == "hello"

    def test_trailing_blank_lines_stripped(self):
        layer = SyntacticLayer()
        assert layer._compress_text("hello\n\n") == "hello"

    def test_only_whitespace_returns_empty(self):
        layer = SyntacticLayer()
        assert layer._compress_text("   \n\n   ") == ""

    def test_empty_string_returns_empty(self):
        layer = SyntacticLayer()
        assert layer._compress_text("") == ""


# ---------------------------------------------------------------------------
# Comment stripping
# ---------------------------------------------------------------------------

class TestStripInlineComment:
    def test_removes_trailing_comment(self):
        assert _strip_inline_comment("x = 1  # set x") == "x = 1"

    def test_no_comment_unchanged(self):
        assert _strip_inline_comment("x = 1") == "x = 1"

    def test_hash_in_single_quotes_preserved(self):
        assert _strip_inline_comment("x = '#not-a-comment'") == "x = '#not-a-comment'"

    def test_hash_in_double_quotes_preserved(self):
        assert _strip_inline_comment('url = "http://example.com/#anchor"') == 'url = "http://example.com/#anchor"'

    def test_full_line_comment_removed(self):
        assert _strip_inline_comment("# this whole line is a comment") == ""

    def test_empty_line_unchanged(self):
        assert _strip_inline_comment("") == ""


class TestCommentStrippingOption:
    def test_comment_stripped_when_enabled(self):
        layer = SyntacticLayer(strip_comments=True)
        assert layer._compress_text("x = 1  # set x") == "x = 1"

    def test_comment_preserved_when_disabled(self):
        layer = SyntacticLayer(strip_comments=False)
        result = layer._compress_text("x = 1  # set x")
        assert "# set x" in result

    def test_full_line_comment_becomes_blank_and_is_collapsed(self):
        layer = SyntacticLayer(strip_comments=True)
        result = layer._compress_text("# comment\ncode = 1")
        assert result == "code = 1"

    def test_hash_in_string_not_stripped(self):
        layer = SyntacticLayer(strip_comments=True)
        result = layer._compress_text('url = "http://x.com/#anchor"')
        assert result == 'url = "http://x.com/#anchor"'


# ---------------------------------------------------------------------------
# Message-level compression
# ---------------------------------------------------------------------------

class TestStringContent:
    def test_content_compressed(self):
        layer = SyntacticLayer()
        msg = {"role": "user", "content": "hello   \n\n\nworld"}
        result = layer._compress_message(msg)
        assert result["content"] == "hello\n\nworld"

    def test_other_fields_preserved(self):
        layer = SyntacticLayer()
        msg = {"role": "user", "content": "hi", "extra": "data"}
        result = layer._compress_message(msg)
        assert result["role"] == "user"
        assert result["extra"] == "data"

    def test_original_message_not_mutated(self):
        layer = SyntacticLayer()
        original = "hello   \n\n\n"
        msg = {"role": "user", "content": original}
        layer._compress_message(msg)
        assert msg["content"] == original


class TestListContent:
    def test_text_block_compressed(self):
        layer = SyntacticLayer()
        msg = {"role": "user", "content": [{"type": "text", "text": "hello   \n\n\nworld"}]}
        result = layer._compress_message(msg)
        assert result["content"][0]["text"] == "hello\n\nworld"

    def test_non_text_block_unchanged(self):
        layer = SyntacticLayer()
        image = {"type": "image", "source": {"type": "base64", "data": "abc"}}
        msg = {"role": "user", "content": [image]}
        result = layer._compress_message(msg)
        assert result["content"][0] == image

    def test_mixed_blocks_only_text_compressed(self):
        layer = SyntacticLayer()
        image = {"type": "image", "source": {"type": "base64", "data": "abc"}}
        text = {"type": "text", "text": "hello   "}
        msg = {"role": "user", "content": [text, image]}
        result = layer._compress_message(msg)
        assert result["content"][0]["text"] == "hello"
        assert result["content"][1] == image

    def test_tool_result_block_unchanged(self):
        layer = SyntacticLayer()
        tool = {"type": "tool_result", "tool_use_id": "x", "content": "output"}
        msg = {"role": "user", "content": [tool]}
        result = layer._compress_message(msg)
        assert result["content"][0] == tool


class TestNoContent:
    def test_message_without_content_unchanged(self):
        layer = SyntacticLayer()
        msg = {"role": "assistant"}
        assert layer._compress_message(msg) == msg

    def test_none_content_unchanged(self):
        layer = SyntacticLayer()
        msg = {"role": "user", "content": None}
        assert layer._compress_message(msg) == msg


# ---------------------------------------------------------------------------
# compress_messages + stats
# ---------------------------------------------------------------------------

class TestCompressMessages:
    def test_multiple_messages(self):
        layer = SyntacticLayer()
        messages = [
            {"role": "user", "content": "hello   "},
            {"role": "assistant", "content": "world   "},
        ]
        result = layer.compress_messages(messages)
        assert result[0]["content"] == "hello"
        assert result[1]["content"] == "world"

    def test_empty_list(self):
        layer = SyntacticLayer()
        assert layer.compress_messages([]) == []

    def test_stats_updated(self):
        layer = SyntacticLayer()
        layer.compress_messages([{"role": "user", "content": "hello   \n\n\n"}])
        stats = layer.get_stats()
        assert stats.chars_in > stats.chars_out
        assert stats.savings_ratio > 0

    def test_stats_accumulate_across_calls(self):
        layer = SyntacticLayer()
        msg = {"role": "user", "content": "hello   "}
        layer.compress_messages([msg])
        stats_after_first = layer.get_stats().chars_in
        layer.compress_messages([msg])
        assert layer.get_stats().chars_in == stats_after_first * 2

    def test_reset_clears_stats(self):
        layer = SyntacticLayer()
        layer.compress_messages([{"role": "user", "content": "hello   "}])
        layer.reset_stats()
        stats = layer.get_stats()
        assert stats.chars_in == 0
        assert stats.chars_out == 0

    def test_no_savings_when_already_clean(self):
        layer = SyntacticLayer()
        layer.compress_messages([{"role": "user", "content": "hello"}])
        stats = layer.get_stats()
        assert stats.chars_in == stats.chars_out


# ---------------------------------------------------------------------------
# LayerStats
# ---------------------------------------------------------------------------

class TestLayerStats:
    def test_savings_ratio_zero_when_no_input(self):
        stats = LayerStats()
        assert stats.savings_ratio == 0.0

    def test_savings_ratio_calculated_correctly(self):
        stats = LayerStats(chars_in=100, chars_out=75)
        assert stats.savings_ratio == pytest.approx(0.25)

    def test_full_savings(self):
        stats = LayerStats(chars_in=100, chars_out=0)
        assert stats.savings_ratio == 1.0

    def test_no_savings(self):
        stats = LayerStats(chars_in=100, chars_out=100)
        assert stats.savings_ratio == 0.0
