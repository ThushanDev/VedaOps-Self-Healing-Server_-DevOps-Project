"""Read a Telegram chat ID from the bot's latest update without printing its token."""

import json
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


def read_bot_token() -> str:
    env_path = Path(".env")
    if not env_path.is_file():
        raise RuntimeError(".env is missing; copy .env.example and set TELEGRAM_BOT_TOKEN")
    for line in env_path.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip() == "TELEGRAM_BOT_TOKEN":
            token = value.strip().strip('"').strip("'")
            if token:
                return token
    raise RuntimeError("TELEGRAM_BOT_TOKEN is blank in .env")


def main() -> int:
    try:
        token = read_bot_token()
        request = Request(
            f"https://api.telegram.org/bot{token}/getUpdates",
            headers={"User-Agent": "VedaOps-local-setup"},
        )
        with urlopen(request, timeout=10) as response:
            payload = json.load(response)
        if not payload.get("ok"):
            print("Telegram rejected the request. Check the bot token in .env.", file=sys.stderr)
            return 1
        updates = payload.get("result", [])
        chats = {}
        for update in updates:
            message = update.get("message") or update.get("channel_post") or {}
            chat = message.get("chat", {})
            if chat.get("id") is not None:
                chats[chat["id"]] = chat
        if not chats:
            print("No chat found. Send /start to your bot, then run this script again.")
            return 1
        for chat_id, chat in chats.items():
            description = chat.get("title") or chat.get("username") or chat.get("first_name") or "chat"
            print(f"Chat ID: {chat_id} ({description})")
        return 0
    except (OSError, URLError, json.JSONDecodeError, RuntimeError):
        print(
            "Could not get chat updates. Check your network and Telegram setup; "
            "the bot token was not printed.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
