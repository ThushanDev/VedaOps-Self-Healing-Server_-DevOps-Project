# Optional integrations

## Anthropic diagnosis

1. Create an API key in the Anthropic Console and confirm billing or spending limits for the account.
2. Put the key in the ignored local `.env` file as `ANTHROPIC_API_KEY=...`. Do not put it in a command, README, GitHub issue, or source file.
3. Keep `CLAUDE_MODEL=claude-sonnet-5` or change it to an API model available to your account.
4. Recreate the healer: `docker compose up -d --force-recreate healer`.
5. The healer sends at most one AI request per minute and only sends up to 8,000 redacted log characters. If the key is missing, the API fails, or the response is invalid, its action is `notify_human`.

## Telegram incident messages

1. In Telegram, open `@BotFather`, create a bot named `VedaOps`, and choose an available username such as `vedaops_bot`.
2. Store the token in `.env` as `TELEGRAM_BOT_TOKEN=...`. Keep the token private.
3. Open the new bot in Telegram and send `/start`.
4. From the project root, run `python scripts/get-telegram-chat-id.py`. The script reads `.env`, requests the bot's updates over HTTPS, and prints chat IDs without printing the token. Select your private chat ID.
5. Put that ID in `.env` as `TELEGRAM_CHAT_ID=...` and recreate the healer.
6. Run the local chaos demo. The message uses the VedaOps incident fields: alert, cause, action, and result.

The `.env` file is ignored by Git. If a key or bot token is exposed, revoke it at the provider and replace it before continuing.
