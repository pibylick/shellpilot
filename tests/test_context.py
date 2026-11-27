import unittest

from shellpilot.context import TerminalSanitizer, build_context, redact, sanitize


class ContextTests(unittest.TestCase):
    def test_masks_tokens_and_url_credentials(self):
        text = "token=sk-abcdefghijklmnopqrstuvwxyz0123456789 https://alice:secret@example.com/x"
        result = redact(text)
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz", result)
        self.assertNotIn("alice:secret", result)
        self.assertIn("[REDACTED]", result)

    def test_removes_terminal_control_sequences(self):
        self.assertEqual(sanitize("a\x1b[31mb\x1b]0;secret\x07c\x00d"), "abcd")

    def test_streaming_sanitizer_hides_split_osc_payload(self):
        cleaner = TerminalSanitizer()
        self.assertEqual(cleaner.feed("ok\x1b]0;secret"), "ok")
        self.assertEqual(cleaner.feed("-title\x07done"), "done")

    def test_context_bounds_output_and_marks_combined(self):
        result = build_context("cmux:abc", "/tmp", "false", 1, "x" * 40000)
        self.assertEqual(result["last_output"]["stream"], "combined")
        self.assertLessEqual(len(result["scrollback"]["text"].encode()), 32768)
        self.assertIsNone(result["stdout"])
        self.assertIsNone(result["stderr"])


if __name__ == "__main__":
    unittest.main()
