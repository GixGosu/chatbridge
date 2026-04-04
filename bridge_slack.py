#!/usr/bin/env python3
"""Slack bridge for Claude Code CLI."""

import logging

from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from core import BridgeBase

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("claude-bridge.slack")


class SlackBridge(BridgeBase):

    platform = "Slack"

    def __init__(self, config_path="config.json"):
        super().__init__(config_path)
        self.bot_id = None
        self.app = AsyncApp(token=self.cfg["bot_token"], name="claude-bridge")
        self._setup_events()

    def _setup_events(self):
        @self.app.event("app_mention")
        async def handle_mention(event, say):
            await self.handle_message(event, say)

        @self.app.event("message")
        async def handle_dm(event, say):
            # Only handle DMs (im channels) — mentions are handled above
            if event.get("channel_type") == "im":
                await self.handle_message(event, say)

    def clean_message(self, text: str) -> str:
        if self.bot_id:
            text = text.replace(f"<@{self.bot_id}>", "").strip()
        return text

    async def handle_message(self, event: dict, say):
        if event.get("bot_id"):
            return

        text = self.clean_message(event.get("text", ""))
        if not text:
            return

        channel_id = event.get("channel", "")
        channel_name = channel_id  # Slack doesn't include channel name in events
        log.info(f"[{channel_id}] {text[:80]}...")

        response = await self.call_claude(channel_id, channel_name, text)

        # Slack has no hard message limit but long messages get truncated in the UI
        MAX = 4000
        if len(response) <= MAX:
            await say(response)
        else:
            for i in range(0, len(response), MAX):
                await say(response[i:i+MAX])

    async def run(self):
        auth = await self.app.client.auth_test()
        self.bot_id = auth["user_id"]
        log.info(f"Bot: {auth.get('user', 'unknown')} ({self.bot_id})")

        handler = AsyncSocketModeHandler(self.app, self.cfg["app_token"])
        log.info("Connected via Socket Mode")
        await handler.start_async()


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(SlackBridge().run())
    except KeyboardInterrupt:
        log.info("Shutting down")
