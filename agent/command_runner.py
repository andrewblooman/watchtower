"""Records shell commands and AWS tool calls to the investigation session."""
from __future__ import annotations

import shlex
import subprocess
from datetime import UTC, datetime
from typing import Any

from agent.session import InvestigationSession


class CommandRunner:
    """Executes shell commands and records all commands/tool calls to the session."""

    def __init__(self, session: InvestigationSession) -> None:
        self._session = session

    def run_shell(self, command: str, timeout: int = 60) -> dict[str, Any]:
        """Run a shell command, record it, and return the result record.

        The command string is tokenised with shlex.split (shell=False) to
        prevent shell injection.  Pipelines and shell builtins are not
        supported; use explicit arg lists for complex commands.
        """
        ts = datetime.now(UTC).isoformat()
        print(f"[cmd] $ {command}", flush=True)
        try:
            args = shlex.split(command)
            proc = subprocess.run(
                args,
                shell=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            record: dict[str, Any] = {
                "ts": ts,
                "type": "shell",
                "command": command,
                "args": None,
                "stdout": proc.stdout[:4096] if proc.stdout else "",
                "stderr": proc.stderr[:2048] if proc.stderr else "",
                "exit_code": proc.returncode,
                "result": None,
            }
        except subprocess.TimeoutExpired:
            record = {
                "ts": ts,
                "type": "shell",
                "command": command,
                "args": None,
                "stdout": "",
                "stderr": f"Timed out after {timeout}s",
                "exit_code": -1,
                "result": None,
            }
        except ValueError as exc:
            # shlex.split can raise ValueError on malformed input (e.g. unclosed quotes)
            record = {
                "ts": ts,
                "type": "shell",
                "command": command,
                "args": None,
                "stdout": "",
                "stderr": f"Invalid command syntax: {exc}",
                "exit_code": -1,
                "result": None,
            }
        self._session.append_command(record)
        return record

    def record_tool(self, name: str, params: dict[str, Any], result: Any) -> dict[str, Any]:
        """Record an AWS API tool call (not a subprocess — audit logging only)."""
        record: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(),
            "type": "tool",
            "command": name,
            "args": params,
            "stdout": None,
            "stderr": None,
            "exit_code": None,
            "result": (
                result
                if isinstance(result, (dict, list, str, int, float, bool, type(None)))
                else str(result)
            ),
        }
        self._session.append_command(record)
        return record
