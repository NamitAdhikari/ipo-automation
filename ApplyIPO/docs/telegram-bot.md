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

1. Start the bot you just created (search its username in Telegram, hit **Start**)
2. Run the bot locally once:
   ```bash
   .venv/bin/python3 bot.py
   ```
3. Send `/start` to your bot in Telegram
4. The bot replies with your chat ID — copy it

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
    "timezone": "Asia/Kathmandu"
  }
}
```

- **`chat_ids`** — list of numeric chat IDs allowed to use the bot and receive notifications. Add multiple for family accounts.
- **`auto_apply.enabled`** — set to `true` to apply automatically every day at the configured time.
- **`auto_apply.time`** — 24-hour format (`"10:00"`)
- **`auto_apply.timezone`** — any valid tz name, e.g. `"Asia/Kathmandu"`

---

## 4. Register bot commands *(optional)*

This adds a command menu inside Telegram (the `/` button). Not required — commands work without it.

1. Message **[@BotFather](https://t.me/BotFather)**
2. Send `/setcommands`, select your bot
3. Paste:
   ```
   start - Get your chat ID
   check - Check open IPOs
   apply - Apply to all open IPOs
   ```

---

## 5. Run the bot

```bash
.venv/bin/python3 bot.py
```

To run it as a background service that starts on login and restarts on crash, see [`scripts/README.md`](../scripts/README.md).

---

## Commands

| Command | What it does |
|---------|-------------|
| `/start` | Shows your chat ID — useful when setting up a new account |
| `/check` | Lists all currently open IPOs across your accounts |
| `/apply` | Applies to every open IPO for all enabled accounts |

All commands work instantly — no confirmation prompts.

---

## Auto-apply

When `auto_apply.enabled` is `true`, the bot runs a check every day at the configured time.  
**If IPOs are open** — it applies and sends you a summary.  
**If nothing is open** — it does nothing. No message, no noise.
