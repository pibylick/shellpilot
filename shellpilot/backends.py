"""Read structured events from locally authenticated agent CLIs."""

import json
import shutil
import subprocess
from collections.abc import Callable

from .context import redact


class BackendError(RuntimeError):
    pass


_CODEX_DISABLED = ("shell_tool", "browser_use", "computer_use", "apps", "hooks")
_TOOL_ITEMS = {"command_execution", "file_change", "mcp_tool_call", "web_search", "tool_call"}


def _command(backend: str, session_id: str | None) -> list[str]:
    if backend == "claude":
        args = ["claude", "-p", "--input-format", "stream-json", "--output-format", "stream-json",
                "--verbose", "--include-partial-messages", "--tools", "",
                "--disallowedTools", "mcp__*", "--setting-sources", "", "--strict-mcp-config"]
        if session_id:
            args += ["--resume", session_id]
        return args
    if backend == "codex":
        args = ["codex", "exec"]
        if session_id:
            args += ["resume"]
        args += ["--json", "--skip-git-repo-check", "-c", 'sandbox_mode="read-only"',
                 "-c", 'approval_policy="never"', "-c", "mcp_servers={}"]
        for feature in _CODEX_DISABLED:
            args += ["--disable", feature]
        if session_id:
            args.append(session_id)
        args.append("-")
        return args
    raise BackendError("unsupported backend")


def run_agent(backend: str, prompt: str, session_id: str | None, cwd: str,
              on_delta: Callable[[str], None], popen=subprocess.Popen) -> tuple[str, str]:
    args = _command(backend, session_id)
    if popen is subprocess.Popen and shutil.which(args[0]) is None:
        raise BackendError(f"{args[0]} CLI is not installed")
    try:
        proc = popen(args, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE, text=True, bufsize=1)
    except OSError as exc:
        raise BackendError(f"cannot start {backend} CLI") from exc
    try:
        if getattr(proc, "stdin", None) is not None:
            if backend == "claude":
                message = {"type": "user", "message": {"role": "user", "content": prompt}}
                proc.stdin.write(json.dumps(message) + "\n")
            else:
                proc.stdin.write(prompt)
            proc.stdin.close()
        parts: list[str] = []
        final_text = ""
        new_session = session_id
        completed = False
        for line in proc.stdout:
            try:
                event = json.loads(line)
            except (ValueError, TypeError) as exc:
                raise BackendError("agent emitted invalid JSON") from exc
            kind = event.get("type")
            if backend == "claude":
                if kind == "system" and event.get("session_id"):
                    new_session = event["session_id"]
                elif kind == "stream_event":
                    inner = event.get("event", {})
                    if inner.get("type") == "content_block_start" and inner.get("content_block", {}).get("type") == "tool_use":
                        raise BackendError("Claude attempted to use a tool")
                    delta = inner.get("delta", {})
                    if delta.get("type") == "text_delta":
                        chunk = delta.get("text", "")
                        parts.append(chunk)
                        on_delta(chunk)
                elif kind == "assistant":
                    for block in event.get("message", {}).get("content", []):
                        if block.get("type") == "tool_use":
                            raise BackendError("Claude attempted to use a tool")
                elif kind == "result":
                    if event.get("is_error"):
                        raise BackendError("Claude turn failed")
                    completed = True
                    new_session = event.get("session_id") or new_session
                    final_text = event.get("result", "")
            else:
                if kind == "thread.started":
                    new_session = event.get("thread_id") or new_session
                elif kind in ("item.started", "item.updated", "item.completed"):
                    item = event.get("item", {})
                    if item.get("type") in _TOOL_ITEMS or item.get("type", "").endswith("tool_call"):
                        raise BackendError("Codex attempted to use a tool")
                    if kind == "item.completed" and item.get("type") == "agent_message":
                        chunk = item.get("text", "")
                        parts.append(chunk)
                        on_delta(chunk)
                elif kind == "turn.completed":
                    completed = True
                elif kind == "turn.failed":
                    raise BackendError("Codex turn failed")
        code = proc.wait()
        if code != 0:
            detail = redact(proc.stderr.read(2048)).strip().splitlines()
            message = detail[-1] if detail else "process exited with an error"
            raise BackendError(f"{backend}: {message}")
        if not completed:
            raise BackendError(f"{backend} turn did not complete")
        answer = "".join(parts) or final_text
        if not parts and answer:
            on_delta(answer)
        if not new_session:
            raise BackendError(f"{backend} did not provide a session ID")
        return answer, new_session
    except BaseException:
        if getattr(proc, "returncode", None) is None:
            proc.kill()
            proc.wait()
        raise
