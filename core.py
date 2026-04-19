#!/usr/bin/env python3
"""Shared core for Claude Code chat bridges."""

import asyncio, json, logging, subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

log = logging.getLogger("claude-bridge")

SESSIONS_FILE = Path(__file__).parent / "sessions.json"


def load_json(path: Path, default=None):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default if default is not None else {}


def save_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2))


def read_if_exists(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def build_system_prompt(workspace: Path, platform: str, channel_name: str = "") -> str:
    """Build context from workspace files. Channel-specific context layered on top."""
    parts = []

    for fname, label in [
        ("SOUL.md", "Personality"),
        ("USER.md", "About the user"),
        ("MEMORY.md", "Long-term memory"),
    ]:
        content = read_if_exists(workspace / fname)
        if content:
            parts.append(f"## {label}\n{content}")

    today = datetime.now().strftime("%Y-%m-%d")
    daily = read_if_exists(workspace / "memory" / f"{today}.md")
    if daily:
        parts.append(f"## Today's notes ({today})\n{daily}")

    if channel_name:
        ctx = read_if_exists(workspace / "channel-contexts" / f"{channel_name}.md")
        if ctx:
            parts.append(f"## Channel context: #{channel_name}\n{ctx}")

    custom = read_if_exists(workspace / "SYSTEM.md")
    if custom:
        parts.append(f"## Additional instructions\n{custom}")

    parts.append(
        "## Runtime\n"
        f"You are running through a minimal {platform} bridge. "
        f"You are connected to Claude Code CLI. You have file read/write/edit and bash.\n"
        f"Your workspace is at: {workspace}\n\n"
        "## Memory\n"
        "- Long-term memory: MEMORY.md (read and update as needed)\n"
        "- Daily notes: memory/YYYY-MM-DD.md (create today's if it doesn't exist)\n"
        "- When asked to remember something, write it to the appropriate file\n"
        "- When asked about past events, read MEMORY.md and recent daily notes\n\n"
        "## Behavior\n"
        "Respond conversationally for chat. Keep responses concise. "
        "Use markdown formatting where supported."
    )

    return "\n\n".join(parts)


def run_claude(message: str, session_id: Optional[str], channel_name: str, model: str, workspace: Path, platform: str) -> tuple[str, str]:
    """Call claude CLI, return (response_text, session_id)."""
    cmd = ["claude", "-p", "--output-format", "json", "--model", model]

    if session_id:
        cmd.extend(["--resume", session_id])
    else:
        cmd.extend(["--append-system-prompt", build_system_prompt(workspace, platform, channel_name)])

    cmd.append(message)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    except subprocess.TimeoutExpired:
        return "Request timed out (60 min limit).", session_id or ""
    except Exception as e:
        log.error(f"Claude CLI error: {e}")
        return f"Error running Claude: {e}", session_id or ""

    if result.returncode != 0:
        log.error(f"Claude CLI exit {result.returncode}: {result.stderr[:500]}")
        return "Claude returned an error. Check logs.", session_id or ""

    try:
        data = json.loads(result.stdout)
        text = data.get("result", data.get("content", result.stdout))
        sid = data.get("session_id", session_id or "")

        # Debug logging
        log.info(f"Claude response length: {len(text)} chars")
        log.info(f"Response preview: {text[:200]}...")

        return text, sid
    except json.JSONDecodeError:
        return result.stdout.strip(), session_id or ""


class BridgeBase:
    """Base class for all chat platform bridges."""

    platform = "unknown"

    def __init__(self, config_path="config.json"):
        self.cfg = load_json(Path(config_path))
        self.workspace = Path(self.cfg.get("workspace_path", "."))
        self.sessions = load_json(SESSIONS_FILE)
        self.model = self.cfg.get("claude_model", "claude-opus-4-6")

    async def call_claude(self, channel_id: str, channel_name: str, message: str) -> str:
        """Run Claude in a thread, manage sessions, return response text."""
        session_id = self.sessions.get(channel_id)

        loop = asyncio.get_running_loop()
        response, new_sid = await loop.run_in_executor(
            None, run_claude, message, session_id, channel_name, self.model, self.workspace, self.platform
        )

        if new_sid and new_sid != session_id:
            self.sessions[channel_id] = new_sid
            save_json(SESSIONS_FILE, self.sessions)

        return response
