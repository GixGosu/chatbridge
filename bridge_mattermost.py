#!/usr/bin/env python3
"""Mattermost bridge for Claude Code CLI."""

import asyncio, json, logging
from typing import Optional

import httpx, websockets

from core import BridgeBase

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("claude-bridge.mattermost")


class MattermostBridge(BridgeBase):

    platform = "Mattermost"

    def __init__(self, config_path="config.json"):
        super().__init__(config_path)
        self.bot_id = ""
        self.bot_username = ""
        self.channels = {}
        self.http: Optional[httpx.AsyncClient] = None

    async def _api(self, method, path, **kwargs):
        headers = {"Authorization": f"Bearer {self.cfg['bot_token']}"}
        resp = await getattr(self.http, method)(
            f"{self.cfg['mattermost_url']}/api/v4{path}",
            headers=headers, **kwargs
        )
        resp.raise_for_status()
        return resp.json() if resp.content else None

    async def init(self):
        self.http = httpx.AsyncClient(timeout=30)
        me = await self._api("get", "/users/me")
        self.bot_id = me["id"]
        self.bot_username = me["username"]
        log.info(f"Bot: @{self.bot_username} ({self.bot_id})")

        channels = await self._api("get", f"/users/me/teams/{self.cfg['team_id']}/channels")
        for c in channels:
            self.channels[c["id"]] = {
                "name": c.get("name", ""),
                "display_name": c.get("display_name", ""),
                "type": c.get("type", ""),
            }
        log.info(f"Monitoring {len(self.channels)} channels")

    async def send_typing(self, channel_id: str):
        try:
            await self._api("post", "/users/me/typing", json={"channel_id": channel_id})
        except Exception:
            pass

    async def send_message(self, channel_id: str, text: str):
        MAX = 16000
        if len(text) <= MAX:
            await self._api("post", "/posts", json={"channel_id": channel_id, "message": text})
        else:
            for i in range(0, len(text), MAX):
                await self._api("post", "/posts", json={"channel_id": channel_id, "message": text[i:i+MAX]})

    def should_respond(self, post: dict) -> bool:
        if post.get("user_id") == self.bot_id:
            return False

        channel_id = post.get("channel_id", "")
        ch = self.channels.get(channel_id, {})
        message = post.get("message", "")

        if ch.get("type") == "D":
            return True
        if f"@{self.bot_username}" in message:
            return True

        allowed = self.cfg.get("allowed_channels", [])
        if allowed and channel_id in allowed:
            return True

        return False

    def clean_message(self, message: str) -> str:
        return message.replace(f"@{self.bot_username}", "").strip()

    async def handle_event(self, raw: str):
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            return

        if event.get("event") != "posted":
            return

        post = json.loads(event.get("data", {}).get("post", "{}"))
        if not self.should_respond(post):
            return

        channel_id = post["channel_id"]
        message = self.clean_message(post.get("message", ""))
        if not message:
            return

        ch = self.channels.get(channel_id, {})
        channel_name = ch.get("name", "")
        log.info(f"[#{channel_name}] {message[:80]}...")

        await self.send_typing(channel_id)
        response = await self.call_claude(channel_id, channel_name, message)
        await self.send_message(channel_id, response)

    async def run(self):
        await self.init()

        base = self.cfg["mattermost_url"].replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{base}/api/v4/websocket"

        while True:
            try:
                log.info(f"Connecting to {ws_url}...")
                async with websockets.connect(ws_url) as ws:
                    await ws.send(json.dumps({
                        "seq": 1,
                        "action": "authentication_challenge",
                        "data": {"token": self.cfg["bot_token"]}
                    }))
                    log.info("Connected and authenticated")

                    async for msg in ws:
                        await self.handle_event(msg)

            except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError) as e:
                log.warning(f"Connection lost ({e}), reconnecting in 5s...")
                await asyncio.sleep(5)
            except Exception as e:
                log.error(f"Error: {e}", exc_info=True)
                await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(MattermostBridge().run())
    except KeyboardInterrupt:
        log.info("Shutting down")
