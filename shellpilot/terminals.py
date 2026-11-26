"""Read only the terminal surface that launched the current shell."""

import asyncio
import re
import subprocess
from dataclasses import dataclass
from typing import Mapping


class TerminalError(RuntimeError):
    pass


@dataclass(frozen=True)
class TerminalSnapshot:
    panel_key: str
    text: str


_ID = re.compile(r"^[A-Za-z0-9:._-]{1,128}$")


def _cmux(env: Mapping[str, str], runner) -> TerminalSnapshot:
    surface = env.get("CMUX_SURFACE_ID", "")
    if not _ID.fullmatch(surface):
        raise TerminalError("cmux: missing or invalid current surface ID")
    command = ["cmux", "read-screen", "--surface", surface, "--scrollback", "--lines", "200"]
    try:
        result = runner(command, capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise TerminalError("cmux screen unavailable") from exc
    if result.returncode:
        raise TerminalError("cmux screen read failed")
    return TerminalSnapshot(f"cmux:{surface}", result.stdout)


async def _iterm_async(session_id: str) -> TerminalSnapshot:
    try:
        import iterm2
    except ImportError as exc:
        raise TerminalError("iTerm2 Python API package is not installed") from exc
    try:
        connection = await iterm2.Connection.async_create()
        app = await iterm2.async_get_app(connection)
        session = app.get_session_by_id(session_id)
        if session is None or session.session_id != session_id:
            raise TerminalError("iTerm2 session ID was not found")
        async with iterm2.Transaction(connection):
            info = await session.async_get_line_info()
            total = info.scrollback_buffer_height + info.mutable_area_height
            count = min(200, total)
            lines = await session.async_get_contents(info.overflow + total - count, count)
        text = "\n".join(line.string for line in lines)
        return TerminalSnapshot(f"iterm2:{session_id}", text)
    except TerminalError:
        raise
    except Exception as exc:
        raise TerminalError("iTerm2 screen unavailable") from exc


def read_terminal(env: Mapping[str, str], runner=None) -> TerminalSnapshot:
    if "CMUX_SURFACE_ID" in env or "CMUX_WORKSPACE_ID" in env:
        return _cmux(env, runner or subprocess.run)
    if "ITERM_SESSION_ID" in env:
        session_id = env["ITERM_SESSION_ID"].rsplit(":", 1)[-1]
        if not _ID.fullmatch(session_id):
            raise TerminalError("iTerm2: missing or invalid session ID")
        return asyncio.run(_iterm_async(session_id))
    raise TerminalError("cmux or iTerm2 session not detected")
