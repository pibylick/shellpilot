import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from shellpilot.__main__ import main
from shellpilot.state import SessionStore
from shellpilot.terminals import TerminalSnapshot


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = {"SHELLPILOT_STATE_FILE": str(Path(self.tmp.name) / "state.json"),
                    "CMUX_SURFACE_ID": "surface:1"}

    def request(self, args, fields=("question", "false", "1", "/tmp")):
        stdout, stderr = io.StringIO(), io.StringIO()
        stdin = io.BytesIO("\0".join(fields).encode())
        code = main(args, self.env, stdin, stdout, stderr)
        return code, stdout.getvalue(), stderr.getvalue()

    @patch("shellpilot.__main__.read_terminal", return_value=TerminalSnapshot("cmux:surface:1", "screen"))
    @patch("shellpilot.__main__.run_agent", return_value=("answer", "session-a"))
    def test_ask_saves_session_after_success(self, agent, terminal):
        code, output, error = self.request(["ask", "--format", "text"])
        self.assertEqual((code, output), (0, "answer\n"))
        self.assertEqual(SessionStore(Path(self.env["SHELLPILOT_STATE_FILE"])).get_session("cmux:surface:1", "codex"), "session-a")

    @patch("shellpilot.__main__.read_terminal", return_value=TerminalSnapshot("cmux:surface:1", "screen"))
    @patch("shellpilot.__main__.run_agent", return_value=("rm -rf /tmp/example", "s1"))
    def test_cmd_returns_editable_candidate_only(self, agent, terminal):
        code, output, error = self.request(["cmd", "--format", "candidate"])
        self.assertEqual((code, output), (0, "rm -rf /tmp/example\n"))

    @patch("shellpilot.__main__.read_terminal", return_value=TerminalSnapshot("cmux:surface:1", "screen"))
    @patch("shellpilot.__main__.run_agent", return_value=("echo ok\necho bad", "s1"))
    def test_cmd_rejects_multiline_and_does_not_save_session(self, agent, terminal):
        code, output, error = self.request(["cmd", "--format", "candidate"])
        self.assertNotEqual(code, 0)
        self.assertEqual(output, "")
        self.assertIsNone(SessionStore(Path(self.env["SHELLPILOT_STATE_FILE"])).get_session("cmux:surface:1", "codex"))

    def test_backend_choice_and_new_are_per_panel(self):
        code, _, _ = self.request(["backend", "claude"])
        self.assertEqual(code, 0)
        store = SessionStore(Path(self.env["SHELLPILOT_STATE_FILE"]))
        self.assertEqual(store.get_backend("cmux:surface:1"), "claude")
        store.set_session("cmux:surface:1", "claude", "s1")
        code, _, _ = self.request(["new"])
        self.assertEqual(code, 0)
        self.assertIsNone(store.get_session("cmux:surface:1", "claude"))


if __name__ == "__main__":
    unittest.main()
