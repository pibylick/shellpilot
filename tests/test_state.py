import tempfile
import unittest
from pathlib import Path

from shellpilot.state import SessionStore


class StateTests(unittest.TestCase):
    def test_sessions_are_isolated_by_panel_and_backend(self):
        with tempfile.TemporaryDirectory() as td:
            store = SessionStore(Path(td) / "state.json")
            store.set_session("cmux:a", "codex", "one")
            store.set_session("cmux:a", "claude", "two")
            store.set_session("cmux:b", "codex", "three")
            self.assertEqual(store.get_session("cmux:a", "codex"), "one")
            self.assertEqual(store.get_session("cmux:a", "claude"), "two")
            self.assertEqual(store.get_session("cmux:b", "codex"), "three")
            store.reset_session("cmux:a", "codex")
            self.assertIsNone(store.get_session("cmux:a", "codex"))
            self.assertEqual(store.get_session("cmux:a", "claude"), "two")

    def test_backend_choice_is_per_panel_and_file_private(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            store = SessionStore(path)
            store.set_backend("iterm2:a", "claude")
            self.assertEqual(SessionStore(path).get_backend("iterm2:a"), "claude")
            self.assertEqual(store.get_backend("iterm2:b"), "codex")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
