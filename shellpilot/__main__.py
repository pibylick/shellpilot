"""CLI bridge between Zsh and structured local agent clients."""

import argparse
import json
import os
import shutil
import sys
import uuid
from pathlib import Path

from .backends import BackendError, run_agent
from .context import TerminalSanitizer, build_context, redact
from .state import SessionStore
from .terminals import TerminalError, panel_key, read_terminal


def _state_path(env: dict) -> Path:
    return Path(env.get("SHELLPILOT_STATE_FILE", str(Path.home() / "Library/Application Support/ShellPilot/state.json")))


def _request(stdin) -> tuple[str, str, int | None, str]:
    fields = stdin.read().decode("utf-8", errors="replace").split("\0")
    fields += [""] * (4 - len(fields))
    question, command, status, cwd = fields[:4]
    try:
        code = int(status)
    except ValueError:
        code = None
    return question, command, code, cwd or os.getcwd()


def _candidate(text: str) -> str:
    value = text.strip()
    if not value or len(value.encode()) > 4096 or any(ord(c) < 32 or 127 <= ord(c) < 160 for c in value):
        raise ValueError("agent did not return one editable command")
    if value.startswith("```") or value.startswith("$") or value.startswith("#"):
        raise ValueError("agent response is not a plain command")
    return value


def main(argv=None, env=None, stdin=None, stdout=None, stderr=None) -> int:
    env = dict(os.environ if env is None else env)
    stdin = sys.stdin.buffer if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    parser = argparse.ArgumentParser(prog="shellpilot")
    parser.add_argument("action", choices=("ask", "cmd", "fix", "explain", "new", "backend", "doctor"))
    parser.add_argument("value", nargs="?")
    parser.add_argument("--format", choices=("ndjson", "text", "candidate"), default="ndjson")
    args = parser.parse_args(argv)
    request_id = uuid.uuid4().hex

    def emit(kind: str, **fields) -> None:
        stdout.write(json.dumps({"schema_version": 1, "request_id": request_id,
                                 "type": kind, **fields}, ensure_ascii=False) + "\n")
        stdout.flush()

    try:
        if args.action == "doctor":
            result = {"codex": bool(shutil.which("codex")), "claude": bool(shutil.which("claude")),
                      "cmux": bool(env.get("CMUX_SURFACE_ID")), "iterm2": bool(env.get("ITERM_SESSION_ID"))}
            if args.format == "ndjson":
                emit("doctor", **result)
                emit("done", ok=True, reason="completed")
            else:
                stdout.write(json.dumps(result) + "\n")
            return 0
        panel = panel_key(env)
        store = SessionStore(_state_path(env))
        if args.action == "backend":
            if args.value not in ("codex", "claude"):
                raise ValueError("backend must be codex or claude")
            store.set_backend(panel, args.value)
            if args.format == "ndjson":
                emit("backend", backend=args.value, panel_key=panel)
                emit("done", ok=True, reason="completed")
            else:
                stdout.write(args.value + "\n")
            return 0
        backend = store.get_backend(panel)
        if args.action == "new":
            store.reset_session(panel, backend)
            if args.format == "ndjson":
                emit("session", backend=backend, panel_key=panel, session_id=None)
                emit("done", ok=True, reason="completed")
            else:
                stdout.write("New session for this panel.\n")
            return 0
        question, last_command, exit_code, cwd = _request(stdin)
        if args.action in ("ask", "cmd") and not question.strip():
            raise ValueError("empty question or command description")
        if args.action == "fix" and (not last_command or exit_code in (None, 0)):
            raise ValueError("no failed command available in this shell")
        if args.action == "explain" and not last_command:
            raise ValueError("no previous command available in this shell")
        snap = read_terminal(env)
        if snap.panel_key != panel:
            raise TerminalError("terminal adapter returned a different panel")
        context = build_context(panel, cwd, last_command, exit_code, snap.text)
        prompt = json.dumps({"task": args.action, "request": redact(question), "context": context,
                             "instruction": "Answer without tool use. For cmd return only one Zsh command, no Markdown."},
                            ensure_ascii=False)
        chunks: list[str] = []
        terminal_cleaner = TerminalSanitizer()

        def on_delta(chunk: str) -> None:
            chunks.append(chunk)
            if args.action == "cmd":
                return
            safe = terminal_cleaner.feed(chunk)
            if args.format == "text":
                stdout.write(safe)
            elif args.format == "ndjson":
                emit("text_delta", text=safe)
            stdout.flush()

        answer, session = run_agent(backend, prompt, store.get_session(panel, backend), cwd, on_delta)
        if args.action == "cmd":
            command = _candidate(answer)
        elif not chunks and answer:
            on_delta(answer)
        store.set_session(panel, backend, session)
        if args.action == "cmd":
            if args.format in ("candidate", "text"):
                stdout.write(command + "\n")
            else:
                emit("command_candidate", command=command)
        if args.format == "text" and args.action != "cmd":
            stdout.write("\n")
        elif args.format == "ndjson":
            emit("session", backend=backend, panel_key=panel, session_id=session)
            emit("done", ok=True, reason="completed")
        return 0
    except (BackendError, TerminalError, ValueError, OSError) as exc:
        if args.format == "ndjson":
            emit("error", message=str(exc))
            emit("done", ok=False, reason="error")
        else:
            stderr.write(f"shellpilot: {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
