import subprocess
import os
import pty
import select
import signal
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PluginTests(unittest.TestCase):
    def test_source_without_omz_registers_ai(self):
        script = f'source {ROOT / "shellpilot.plugin.zsh"}; whence -w ai'
        result = subprocess.run(["zsh", "-fc", script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ai: function", result.stdout)

    def test_ai_command_does_not_replace_failed_command_metadata(self):
        script = (f'source {ROOT / "shellpilot.plugin.zsh"}; '
                  'shellpilot_preexec "false"; false; shellpilot_precmd; '
                  'shellpilot_preexec "ai fix"; true; shellpilot_precmd; '
                  'print -r -- "$SHELLPILOT_LAST_CMD:$SHELLPILOT_LAST_EXIT"')
        result = subprocess.run(["zsh", "-fc", script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("false:1", result.stdout)

    def test_exit_status_survives_an_earlier_precmd_hook(self):
        script = (f'precmd_functions=(clobber_status); clobber_status() {{ true; }}; '
                  f'source {ROOT / "shellpilot.plugin.zsh"}; '
                  'print -r -- "$precmd_functions[1]"')
        result = subprocess.run(["zsh", "-fc", script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "shellpilot_precmd")

    def test_ctrl_g_only_executes_after_user_enter(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "ran"
            fake = Path(td) / "fake-shellpilot"
            fake.write_text(f"#!/bin/sh\nprintf '%s\\n' 'touch {target}'\n")
            fake.chmod(0o755)
            master, slave = pty.openpty()
            env = dict(os.environ, PROMPT="SHPROMPT> ", SHELLPILOT_BIN=str(fake))
            proc = subprocess.Popen(["zsh", "-f", "-i"], stdin=slave, stdout=slave, stderr=slave,
                                    env=env, start_new_session=True)
            os.close(slave)
            try:
                self._until(master, b"SHPROMPT> ")
                os.write(master, f"source {ROOT / 'shellpilot.plugin.zsh'}\n".encode())
                self._until(master, b"SHPROMPT> ")
                os.write(master, b"make a file\x07")
                time.sleep(0.2)
                self.assertFalse(target.exists(), "generated command ran before Enter")
                os.write(master, b"\n")
                deadline = time.monotonic() + 3
                while not target.exists() and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertTrue(target.exists(), "Enter did not execute edited buffer")
            finally:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=3)
                os.close(master)

    def test_ai_cmd_prefills_next_prompt_without_running_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "ran"
            fake = Path(td) / "fake-shellpilot"
            fake.write_text(f"#!/bin/sh\nprintf '%s\\n' 'touch {target}'\n")
            fake.chmod(0o755)
            master, slave = pty.openpty()
            env = dict(os.environ, PROMPT="SHPROMPT> ", SHELLPILOT_BIN=str(fake))
            proc = subprocess.Popen(["zsh", "-f", "-i"], stdin=slave, stdout=slave, stderr=slave,
                                    env=env, start_new_session=True)
            os.close(slave)
            try:
                self._until(master, b"SHPROMPT> ")
                os.write(master, f"source {ROOT / 'shellpilot.plugin.zsh'}\n".encode())
                self._until(master, b"SHPROMPT> ")
                os.write(master, b"ai cmd make a file\n")
                self._until(master, b"SHPROMPT> ")
                time.sleep(0.2)
                self.assertFalse(target.exists(), "ai cmd ran its candidate before a second Enter")
                os.write(master, b"\n")
                deadline = time.monotonic() + 3
                while not target.exists() and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertTrue(target.exists())
            finally:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=3)
                os.close(master)

    @staticmethod
    def _until(fd, needle):
        output = b""
        deadline = time.monotonic() + 3
        while needle not in output and time.monotonic() < deadline:
            if select.select([fd], [], [], 0.1)[0]:
                output += os.read(fd, 4096)
        if needle not in output:
            raise AssertionError(f"prompt missing: {output!r}")


if __name__ == "__main__":
    unittest.main()
