import io
import json
import unittest

from shellpilot.backends import BackendError, run_agent


class FakeProcess:
    def __init__(self, records, code=0, stderr=""):
        self.stdout = io.StringIO("".join(json.dumps(row) + "\n" for row in records))
        self.stderr = io.StringIO(stderr)
        self.returncode = code
        self.args = None

    def wait(self, timeout=None):
        return self.returncode

    def kill(self):
        self.returncode = -9


class BackendTests(unittest.TestCase):
    def test_claude_streams_deltas_and_records_session(self):
        records = [
            {"type": "system", "subtype": "init", "session_id": "s1"},
            {"type": "stream_event", "event": {"delta": {"type": "text_delta", "text": "hello"}}},
            {"type": "result", "is_error": False, "session_id": "s1", "result": "hello"},
        ]
        calls = []

        def popen(args, **kwargs):
            calls.append(args)
            return FakeProcess(records)

        deltas = []
        text, session = run_agent("claude", "hi", None, "/tmp", deltas.append, popen)
        self.assertEqual((text, session, deltas), ("hello", "s1", ["hello"]))
        self.assertIn("--tools", calls[0])
        self.assertIn("--disallowedTools", calls[0])

    def test_codex_resume_uses_explicit_id_and_refuses_tools(self):
        records = [
            {"type": "thread.started", "thread_id": "c1"},
            {"type": "item.completed", "item": {"type": "agent_message", "text": "answer"}},
            {"type": "turn.completed"},
        ]
        calls = []

        def popen(args, **kwargs):
            calls.append(args)
            return FakeProcess(records)

        text, session = run_agent("codex", "hi", "c1", "/tmp", lambda _: None, popen)
        self.assertEqual((text, session), ("answer", "c1"))
        self.assertIn("resume", calls[0])
        self.assertIn("c1", calls[0])
        self.assertIn("shell_tool", calls[0])
        self.assertIn("hooks", calls[0])
        self.assertNotIn("--last", calls[0])

    def test_codex_rejects_tool_event(self):
        records = [{"type": "item.started", "item": {"type": "command_execution"}}]
        with self.assertRaises(BackendError):
            run_agent("codex", "hi", None, "/tmp", lambda _: None, lambda *a, **k: FakeProcess(records))

    def test_incomplete_turn_does_not_succeed(self):
        with self.assertRaises(BackendError):
            run_agent("claude", "hi", None, "/tmp", lambda _: None, lambda *a, **k: FakeProcess([{"type": "system", "session_id": "s1"}]))

    def test_startup_failure_reports_redacted_diagnostic(self):
        with self.assertRaisesRegex(BackendError, "read-only file system") as failure:
            run_agent("codex", "hi", None, "/tmp", lambda _: None,
                      lambda *a, **k: FakeProcess([], 1, "read-only file system token=sk-abcdefghijklmnopqrstuvwxyz0123456789"))
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz", str(failure.exception))


if __name__ == "__main__":
    unittest.main()
