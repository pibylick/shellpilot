import asyncio
import subprocess
import sys
import types
import unittest
from unittest.mock import patch

from shellpilot.terminals import TerminalError, read_terminal


class CmuxTests(unittest.TestCase):
    def test_reads_explicit_surface_only(self):
        calls = []

        def runner(args, **kwargs):
            calls.append(args)
            return subprocess.CompletedProcess(args, 0, "screen", "")

        snap = read_terminal({"CMUX_SURFACE_ID": "surface:3", "CMUX_WORKSPACE_ID": "workspace:1"}, runner)
        self.assertEqual(snap.panel_key, "cmux:surface:3")
        self.assertEqual(snap.text, "screen")
        self.assertIn("--surface", calls[0])
        self.assertIn("surface:3", calls[0])

    def test_refuses_missing_surface_instead_of_focused_fallback(self):
        with self.assertRaises(TerminalError):
            read_terminal({"CMUX_WORKSPACE_ID": "workspace:1"}, lambda *a, **k: None)

    def test_refuses_failed_read(self):
        def runner(args, **kwargs):
            return subprocess.CompletedProcess(args, 1, "", "missing")
        with self.assertRaises(TerminalError):
            read_terminal({"CMUX_SURFACE_ID": "surface:3"}, runner)


class ITermTests(unittest.TestCase):
    def test_refuses_unknown_session(self):
        class Connection:
            @staticmethod
            async def async_create():
                return object()

        class App:
            def get_session_by_id(self, session_id):
                return None

        fake = types.SimpleNamespace(Connection=Connection, async_get_app=lambda conn: asyncio.sleep(0, result=App()))
        with patch.dict(sys.modules, {"iterm2": fake}):
            with self.assertRaises(TerminalError):
                read_terminal({"ITERM_SESSION_ID": "w0t1p0:ABC"})


if __name__ == "__main__":
    unittest.main()
