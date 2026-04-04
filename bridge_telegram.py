#!/usr/bin/env python3
"""Telegram bridge for Claude Code CLI."""

import logging

from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, filters

from core import BridgeBase

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("claude-bridge.telegram")


class TelegramBridge(BridgeBase):

    platform = "Telegram"

    def __init__(self, config_path="config.json"):
        super().__init__(config_path)
        self.bot_username = None
        self.app = Application.builder().token(self.cfg["bot_token"]).build()
        self._setup_handlers()

    def _setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    @staticmethod
    async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Claude Code bridge is running. Send me a message.")

    def should_respond(self, update: Update) -> bool:
        if not update.message or not update.message.text:
            return False

        # Always respond in private chats
        if update.message.chat.type == "private":
            return True

        # In groups, only respond if @mentioned
        if self.bot_username and f"@{self.bot_username}" in update.message.text:
            return True

        # Check allowed_channels config
        allowed = self.cfg.get("allowed_channels", [])
        if allowed and str(update.message.chat.id) in allowed:
            return True

        return False

    def clean_message(self, text: str) -> str:
        if self.bot_username:
            text = text.replace(f"@{self.bot_username}", "").strip()
        return text

    def channel_name(self, update: Update) -> str:
        chat = update.message.chat
        if chat.type == "private":
            return f"dm-{chat.first_name or chat.username or chat.id}"
        return chat.title or str(chat.id)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.should_respond(update):
            return

        text = self.clean_message(update.message.text)
        if not text:
            return

        ch_id = str(update.message.chat.id)
        ch_name = self.channel_name(update)
        log.info(f"[{ch_name}] {text[:80]}...")

        await update.message.chat.send_action("typing")
        response = await self.call_claude(ch_id, ch_name, text)

        # Telegram has a 4096 char limit per message
        MAX = 4096
        if len(response) <= MAX:
            await update.message.reply_text(response)
        else:
            for i in range(0, len(response), MAX):
                await update.message.reply_text(response[i:i+MAX])

    def run_sync(self):
        # Get bot username on startup
        async def post_init(app):
            bot = await app.bot.get_me()
            self.bot_username = bot.username
            log.info(f"Bot: @{self.bot_username} ({bot.id})")

        self.app.post_init = post_init
        log.info("Starting Telegram polling...")
        self.app.run_polling()


if __name__ == "__main__":
    try:
        TelegramBridge().run_sync()
    except KeyboardInterrupt:
        log.info("Shutting down")
