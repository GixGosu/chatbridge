#!/usr/bin/env python3
"""Discord bridge for Claude Code CLI."""

import logging

import discord

from core import BridgeBase

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("claude-bridge.discord")


class DiscordBridge(BridgeBase):

    platform = "Discord"

    def __init__(self, config_path="config.json"):
        super().__init__(config_path)
        intents = discord.Intents.default()
        intents.message_content = True
        self.client = discord.Client(intents=intents)
        self.bot_id = None
        self._setup_events()

    def _setup_events(self):
        @self.client.event
        async def on_ready():
            self.bot_id = self.client.user.id
            log.info(f"Bot: {self.client.user} ({self.bot_id})")
            log.info(f"In {len(self.client.guilds)} guild(s)")

        @self.client.event
        async def on_message(message):
            await self.handle_message(message)

    def should_respond(self, message: discord.Message) -> bool:
        if message.author.id == self.bot_id:
            return False

        # Always respond to DMs
        if isinstance(message.channel, discord.DMChannel):
            return True

        # Respond if @mentioned
        if self.client.user in message.mentions:
            return True

        # Check allowed_channels config
        allowed = self.cfg.get("allowed_channels", [])
        if allowed and str(message.channel.id) in allowed:
            return True

        return False

    def clean_message(self, message: discord.Message) -> str:
        text = message.content
        if self.client.user:
            text = text.replace(f"<@{self.client.user.id}>", "").strip()
        return text

    def channel_name(self, message: discord.Message) -> str:
        if isinstance(message.channel, discord.DMChannel):
            return f"dm-{message.author.name}"
        return getattr(message.channel, "name", "unknown")

    async def handle_message(self, message: discord.Message):
        if not self.should_respond(message):
            return

        text = self.clean_message(message)
        if not text:
            return

        ch_name = self.channel_name(message)
        ch_id = str(message.channel.id)
        log.info(f"[#{ch_name}] {text[:80]}...")

        async with message.channel.typing():
            response = await self.call_claude(ch_id, ch_name, text)

        # Discord has a 2000 char limit per message
        MAX = 2000
        if len(response) <= MAX:
            await message.channel.send(response)
        else:
            for i in range(0, len(response), MAX):
                await message.channel.send(response[i:i+MAX])

    def run_sync(self):
        self.client.run(self.cfg["bot_token"], log_handler=None)


if __name__ == "__main__":
    try:
        DiscordBridge().run_sync()
    except KeyboardInterrupt:
        log.info("Shutting down")
