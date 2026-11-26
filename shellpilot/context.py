"""Bound and redact terminal text before sending it to an agent."""

import re

_URL_AUTH = re.compile(r"(https?://)[^\s/@:]+:[^\s/@]+@", re.I)
_TOKEN = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16})\b")
_ASSIGNMENT = re.compile(r"(?i)\b((?:api[_-]?key|access[_-]?token|password|secret|authorization)\s*[:=]\s*)[^\s,;]+")


class TerminalSanitizer:
    """Strip terminal controls even when escape sequences span stream chunks."""

    def __init__(self):
        self.state = "text"

    def feed(self, text: str) -> str:
        out = []
        for char in text:
            if self.state == "text":
                if char == "\x1b":
                    self.state = "esc"
                elif char == "\x9b":
                    self.state = "csi"
                elif char == "\x9d":
                    self.state = "osc"
                elif char in "\n\t" or 32 <= ord(char) < 127 or ord(char) >= 160:
                    out.append(char)
            elif self.state == "esc":
                self.state = "csi" if char == "[" else "osc" if char == "]" else "text"
            elif self.state == "csi":
                if "@" <= char <= "~":
                    self.state = "text"
            elif self.state == "osc":
                if char == "\x07":
                    self.state = "text"
                elif char == "\x1b":
                    self.state = "osc_esc"
            elif self.state == "osc_esc":
                self.state = "text" if char == "\\" else "osc"
        return "".join(out)


def sanitize(text: str) -> str:
    return TerminalSanitizer().feed(text)


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
