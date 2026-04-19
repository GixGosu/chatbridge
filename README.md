# claude-bridge

Minimal chat platform bridges for [Claude Code](https://docs.anthropic.com/en/docs/claude-code). Talk to Claude in your chat platform with persistent sessions, per-channel context, and full access to Claude Code's tools (bash, file read/write, etc.).

Supports **Mattermost**, **Discord**, **Slack**, and **Telegram**.

## Quick Start with an AI Coding Assistant (recommended)

The fastest path. Clone the repo, open your AI coding CLI, and talk to it:

```bash
# Claude Code
claude

# Codex
codex

# Any CLI that reads project files works — the CLAUDE.md and README
# give the assistant everything it needs to understand the project.
```

Then just ask it things in natural language:

- **"Set up the Mattermost bridge with my bot token"** — it will create your `config.json`, install deps, and walk you through bot setup
- **"Explain how the system prompt is built"** — it will read `core.py` and the workspace directory structure and break it down
- **"Add a channel context for #project-x"** — it will create the markdown file in your workspace and explain how it gets loaded
- **"Run the Discord bridge and help me debug connection issues"** — it will launch the bridge, read the logs, and troubleshoot with you
- **"Add a new platform adapter"** — it will study the existing adapters, scaffold a new one following the same pattern, and wire it into the shared core

The architecture is simple enough that an AI assistant can fully understand the project from the `CLAUDE.md` and this README.

## Prerequisites

- Python 3.11+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated (`claude` available in PATH)
- A bot account on your platform of choice

## Setup

```bash
git clone https://github.com/GixGosu/chatbridge.git && cd chatbridge
python3 -m venv .venv && source .venv/bin/activate

# Install deps for your platform only:
pip install -r requirements-mattermost.txt
pip install -r requirements-discord.txt
pip install -r requirements-slack.txt
pip install -r requirements-telegram.txt

# Or install everything:
pip install -r requirements.txt
```

Copy the example config for your platform to `config.json` and fill in your values:

```bash
# Pick one:
cp config.example.mattermost.json config.json
cp config.example.discord.json config.json
cp config.example.slack.json config.json
cp config.example.telegram.json config.json
```

## Run

```bash
# Pick one:
python bridge_mattermost.py
python bridge_discord.py
python bridge_slack.py
python bridge_telegram.py
```

## Platform setup

### Mattermost

1. Go to **Integrations > Bot Accounts > Add Bot Account**
2. Copy the bot token into `config.json`
3. Get your team ID from **Team Settings** or `GET /api/v4/teams`
4. Add the bot to channels you want it in

### Discord

1. Create an application at [discord.com/developers](https://discord.com/developers/applications)
2. Go to **Bot** tab, create a bot, copy the token into `config.json`
3. Enable **Message Content Intent** under the bot's Privileged Gateway Intents
4. Invite the bot to your server with the OAuth2 URL generator (scopes: `bot`; permissions: `Send Messages`, `Read Message History`)

### Slack

1. Create an app at [api.slack.com/apps](https://api.slack.com/apps)
2. Enable **Socket Mode** and generate an app-level token (`xapp-...`) — this is `app_token`
3. Under **OAuth & Permissions**, add scopes: `app_mentions:read`, `chat:write`, `im:history`, `im:read`
4. Install to your workspace and copy the bot token (`xoxb-...`) — this is `bot_token`
5. Under **Event Subscriptions**, subscribe to: `app_mention`, `message.im`

### Telegram

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Create a new bot with `/newbot`
3. Copy the token into `config.json`
4. Optionally disable privacy mode with `/setprivacy` if you want the bot to see all group messages

## How it works

1. Connects to your chat platform via its real-time API
2. Listens for @mentions and DMs
3. Builds a system prompt from your workspace context files
4. Spawns `claude` CLI as a subprocess with the message
5. Sends the response back to the channel
6. Maintains per-channel sessions for conversation continuity

## Config

All platforms share these fields:

| Key | Description |
|-----|-------------|
| `workspace_path` | Path to your workspace directory (see below) |
| `claude_model` | Claude model to use (default: `claude-opus-4-6`) |
| `allowed_channels` | Channel IDs the bot responds to without @mention. Empty = @mention/DM only |
| `bot_token` | Bot token for your platform |

Platform-specific fields:

| Platform | Extra fields |
|----------|-------------|
| Mattermost | `mattermost_url`, `team_id` |
| Slack | `app_token` (Socket Mode app-level token) |
| Discord | — |
| Telegram | — |

## Workspace directory

The `workspace_path` is a directory where the bridge loads context files to build the system prompt. All files are optional.

```
workspace/
  SOUL.md              # Bot personality and behavior instructions
  USER.md              # Information about the user(s)
  MEMORY.md            # Long-term memory (can be read/updated by Claude)
  SYSTEM.md            # Additional system prompt instructions (custom tools, paths, etc.)
  memory/
    2026-04-03.md      # Daily notes (auto-referenced by date)
  channel-contexts/
    general.md         # Context loaded only in #general
    project-x.md       # Context loaded only in #project-x
```

The system prompt is assembled from these files on the first message in each channel. Subsequent messages reuse the Claude Code session, so context persists across the conversation.

## Architecture

```
core.py              # Shared logic: system prompt builder, Claude CLI runner, session manager
bridge_mattermost.py # Mattermost adapter (WebSocket + REST)
bridge_discord.py    # Discord adapter (discord.py)
bridge_slack.py      # Slack adapter (Socket Mode via slack-bolt)
bridge_telegram.py   # Telegram adapter (polling via python-telegram-bot)
```

Each adapter is ~80-120 lines. The shared core is ~110 lines. That's it.
