import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class IntegrationTests(unittest.TestCase):
    def test_real_cli_redacts_context_and_resumes_only_own_panel(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            cmux = bin_dir / "cmux"
            cmux.write_text("#!/bin/sh\nprintf '%s\\n' 'token=sk-abcdefghijklmnopqrstuvwxyz0123456789'\n")
            cmux.chmod(0o755)
            codex = bin_dir / "codex"
            codex.write_text("""#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
prompt = sys.stdin.read()
with Path(os.environ['SHP_CAPTURE']).open('a') as f:
    f.write(json.dumps({'args': sys.argv[1:], 'prompt': prompt}) + '\\n')
panel = json.loads(prompt)['context']['panel_key']
print(json.dumps({'type':'thread.started','thread_id':'id-' + panel}))
print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'OK'}}))
print(json.dumps({'type':'turn.completed'}))
""")
            codex.chmod(0o755)
            env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}",
                       SHELLPILOT_STATE_FILE=str(root / "state.json"), SHP_CAPTURE=str(root / "capture.jsonl"))
            for panel in ("surface:1", "surface:2", "surface:1"):
                env["CMUX_SURFACE_ID"] = panel
                result = subprocess.run([sys.executable, "-m", "shellpilot", "ask", "--format", "text"],
                                        input=b"why\0false\01\0/tmp", cwd=ROOT, env=env, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertEqual(result.stdout, b"OK\n")
            entries = [__import__("json").loads(line) for line in (root / "capture.jsonl").read_text().splitlines()]
            self.assertEqual(len(entries), 3)
            self.assertNotIn("abcdefghijklmnopqrstuvwxyz", entries[0]["prompt"])
            self.assertIn("[REDACTED]", entries[0]["prompt"])
            self.assertNotIn("resume", entries[1]["args"])
            self.assertIn("resume", entries[2]["args"])
            self.assertIn("id-cmux:surface:1", entries[2]["args"])


if __name__ == "__main__":
    unittest.main()
