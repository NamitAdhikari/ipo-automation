# Telegram Bot Setup

The bot lets you check open IPOs and apply across all accounts — right from Telegram.  
It can also apply automatically on a schedule, silently, every day.

---

## 1. Create the bot

1. Open Telegram and message **[@BotFather](https://t.me/BotFather)**
2. Send `/newbot` and follow the prompts (name → username)
3. Copy the **bot token** you receive — looks like `123456:ABC-DEF...`

---

## 2. Get your chat ID

You need your numeric chat ID to authorize yourself and receive notifications.

1. Add your bot token to `accounts.json` first (even temporarily):
   ```json
   "telegram": { "bot_token": "123456:ABC-DEF...", "chat_ids": [] }
   ```
2. Run the bot:
   ```bash
   uv run bot.py
   ```
3. **In Telegram:** open your bot and send `/start`
4. The bot replies with your chat ID — copy the number into `chat_ids`

---

## 3. Configure `accounts.json`

Add the token and your chat ID under `settings.telegram`:

```json
"telegram": {
  "bot_token": "123456:ABC-DEF...",
  "chat_ids": [987654321],
  "auto_apply": {
    "enabled": false,
    "time": "10:00",
    "timezone": "Asia/Kathmandu",
    "confirm_before_apply": false
  }
}
```

- **`chat_ids`** — list of numeric chat IDs allowed to use the bot and receive notifications. Add multiple for family accounts.
- **`auto_apply.enabled`** — set to `true` to apply automatically every day at the configured time.
- **`auto_apply.time`** — 24-hour format (`"10:00"`)
- **`auto_apply.timezone`** — any valid tz name, e.g. `"Asia/Kathmandu"`
- **`auto_apply.confirm_before_apply`** — when `true`, the scheduled job sends an inline prompt ("Apply now?" / "Skip") instead of applying automatically; prompt expires at midnight

---

## 4. Register bot commands *(manual, optional)*

> **Requires manual action in Telegram.** This adds the `/` command menu inside the chat — purely cosmetic, commands work fine without it.

1. Message **[@BotFather](https://t.me/BotFather)**
2. Send `/setcommands` and select your bot when prompted
3. Paste the following and send:
   ```
   start - Get your chat ID
   check - Check open IPOs (tap Apply now to apply)
   ```

---

## 5. Run the bot

```bash
uv run bot.py
```

To run it as a background service that starts on login and restarts on crash, see [`scripts/README.md`](../scripts/README.md).

---

## Commands

| Command | Requires manual setup? | What it does |
|---------|----------------------|-------------|
| `/start` | No | Shows your chat ID — useful when adding a new account |
| `/check` | No | Lists open IPOs with issue type, share type, and category; tap **✅ Apply now** to apply inline |

All prompts (inline buttons) expire at midnight so stale buttons in chat history never apply to old results.

---

## Auto-apply

When `auto_apply.enabled` is `true`, the bot runs a check every day at the configured time.  
**If IPOs are open** — it applies and sends you a summary.  
**If nothing is open** — it does nothing. No message, no noise.

Set `confirm_before_apply: true` to receive an inline **Apply now / Skip** prompt instead of auto-applying — useful when you want to stay in control without running `/check` manually.  
The prompt expires at midnight of the same day.
