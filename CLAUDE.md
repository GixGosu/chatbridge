# Claude Bridge

Minimal chat platform bridges that connect Claude Code CLI to Mattermost, Discord, Slack, and Telegram.

## Architecture

```
core.py              — Shared logic: system prompt builder, Claude CLI runner, session manager
bridge_mattermost.py — Mattermost adapter (WebSocket + REST)
bridge_discord.py    — Discord adapter (discord.py)
bridge_slack.py      — Slack adapter (Socket Mode via slack-bolt)
bridge_telegram.py   — Telegram adapter (polling via python-telegram-bot)
```

Each bridge adapter is ~80-120 lines. `core.py` is ~110 lines. All adapters extend `BridgeBase` from `core.py`.

## How it works

1. A bridge connects to a chat platform's real-time API
2. Listens for @mentions and DMs
3. `build_system_prompt()` assembles context from workspace files (SOUL.md, USER.md, MEMORY.md, channel-contexts/, etc.)
4. `run_claude()` spawns `claude -p` as a subprocess with the message and system prompt
5. Response is sent back to the channel
6. Per-channel sessions are stored in `sessions.json` for conversation continuity

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-<platform>.txt   # or requirements.txt for all
cp config.example.<platform>.json config.json  # fill in your bot token and settings
python bridge_<platform>.py
```

## Config

`config.json` (gitignored) — requires at minimum:
- `workspace_path` — directory with context files (SOUL.md, USER.md, etc.)
- `bot_token` — your platform's bot token
- `claude_model` — defaults to `claude-opus-4-6`
- `allowed_channels` — channel IDs for unprompted listening (empty = @mention/DM only)

Platform-specific: Mattermost needs `mattermost_url` and `team_id`. Slack needs `app_token`.

## Workspace directory

The `workspace_path` directory provides context to Claude via the system prompt:

```
workspace/
  SOUL.md              # Bot personality and behavior
  USER.md              # Info about the user(s)
  MEMORY.md            # Long-term memory (read/updated by Claude)
  SYSTEM.md            # Additional system prompt instructions
  memory/
    YYYY-MM-DD.md      # Daily notes
  channel-contexts/
    <channel-name>.md  # Per-channel context
```

## Key functions in core.py

- `build_system_prompt(workspace, platform, channel_name)` — assembles all workspace context files into a system prompt
- `run_claude(message, session_id, channel_name, model, workspace, platform)` — calls `claude` CLI, returns `(response_text, session_id)`
- `BridgeBase` — base class handling config loading, session persistence, and async Claude invocation

## Adding a new platform

1. Create `bridge_<platform>.py`
2. Subclass `BridgeBase`, set `self.platform`
3. Implement the platform's real-time message listener
4. Call `await self.call_claude(channel_id, channel_name, message)` on incoming messages
5. Send the response back via the platform's API
6. Add `requirements-<platform>.txt` and `config.example.<platform>.json`
