"""Small private state file containing only panel/backend session IDs."""

import fcntl
import json
import os
import tempfile
from pathlib import Path


class SessionStore:
    def __init__(self, path: Path):
        self.path = Path(path)

    def _read(self) -> dict:
        try:
            data = json.loads(self.path.read_text())
            return data if isinstance(data, dict) else {}
        except (FileNotFoundError, ValueError, OSError):
            return {}

    def _update(self, change) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        lock_path = self.path.with_suffix(".lock")
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        with os.fdopen(fd, "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            data = self._read()
            change(data)
            temp_fd, name = tempfile.mkstemp(prefix=".state-", dir=self.path.parent)
            try:
                with os.fdopen(temp_fd, "w") as out:
                    json.dump(data, out, sort_keys=True)
                    out.flush()
                    os.fsync(out.fileno())
                os.replace(name, self.path)
            finally:
                if os.path.exists(name):
                    os.unlink(name)

    def get_session(self, panel: str, backend: str) -> str | None:
        return self._read().get(panel, {}).get("sessions", {}).get(backend)

    def set_session(self, panel: str, backend: str, session_id: str) -> None:
        self._update(lambda data: data.setdefault(panel, {}).setdefault("sessions", {}).__setitem__(backend, session_id))

    def reset_session(self, panel: str, backend: str) -> None:
        self._update(lambda data: data.setdefault(panel, {}).setdefault("sessions", {}).pop(backend, None))

    def get_backend(self, panel: str) -> str:
        return self._read().get(panel, {}).get("backend", "codex")

    def set_backend(self, panel: str, backend: str) -> None:
        if backend not in ("codex", "claude"):
            raise ValueError("unsupported backend")
        self._update(lambda data: data.setdefault(panel, {}).__setitem__("backend", backend))
