"""Bound and redact terminal text before sending it to an agent."""

import re

_OSC = re.compile(r"\x1b\].*?(?:\x07|\x1b\\)", re.DOTALL)
_CSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_ESC = re.compile(r"\x1b[@-_]")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")
_URL_AUTH = re.compile(r"(https?://)[^\s/@:]+:[^\s/@]+@", re.I)
_TOKEN = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16})\b")
_ASSIGNMENT = re.compile(r"(?i)\b((?:api[_-]?key|access[_-]?token|password|secret|authorization)\s*[:=]\s*)[^\s,;]+")


def sanitize(text: str) -> str:
    text = _OSC.sub("", text)
    text = _CSI.sub("", text)
    text = _ESC.sub("", text)
    return _CONTROL.sub("", text)


def redact(text: str) -> str:
    text = sanitize(text)
    text = _URL_AUTH.sub(r"\1[REDACTED]@", text)
    text = _TOKEN.sub("[REDACTED]", text)
    return _ASSIGNMENT.sub(r"\1[REDACTED]", text)


def _tail(text: str, byte_limit: int, line_limit: int | None = None) -> str:
    if line_limit is not None:
        text = "\n".join(text.splitlines()[-line_limit:])
    data = text.encode("utf-8")[-byte_limit:]
    return data.decode("utf-8", errors="ignore")


def build_context(panel_key: str, cwd: str, last_command: str, exit_code: int | None,
                  scrollback: str, last_output: str | None = None) -> dict:
    clean_screen = _tail(redact(scrollback), 32768, 200)
    clean_output = _tail(redact(last_output), 16384) if last_output is not None else None
    return {
        "panel_key": panel_key,
        "cwd": _tail(redact(cwd), 4096),
        "last_command": _tail(redact(last_command), 4096),
        "exit_code": exit_code,
        "scrollback": {"text": clean_screen, "stream": "combined", "available": bool(scrollback)},
        "last_output": {"text": clean_output, "stream": "combined", "available": last_output is not None},
        "stdout": None,
        "stderr": None,
    }
