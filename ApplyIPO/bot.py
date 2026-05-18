#!/usr/bin/env python3
"""
Meroshare IPO Telegram Bot

Listens for Telegram bot commands and runs IPO checks/applications.

Configuration: accounts.json -> settings -> telegram_bot_token

Commands:
  /start  — Get your Telegram chat ID (needed for notification setup)
  /check  — Check all accounts for applicable IPOs and report results
  /apply  — Check then apply for all applicable IPOs across all accounts

Scheduling:
  Set accounts.json -> settings -> auto_apply -> enabled: true to automatically
  check and apply every day at the configured time.
"""

import datetime
import json
import logging
import sys
import zoneinfo
from pathlib import Path

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from check_ipos import AccountCheckResult, check_all_accounts
from run_accounts import AccountApplyResult, apply_all_accounts

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

CONFIG_FILE = Path(__file__).parent / "accounts.json"


def load_config() -> dict:
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("accounts.json not found at %s", CONFIG_FILE)
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in accounts.json: %s", e)
        sys.exit(1)


def _telegram_cfg(config: dict) -> dict:
    return config.get("settings", {}).get("telegram", {})


def get_token(config: dict) -> str:
    token = _telegram_cfg(config).get("bot_token", "")
    if not token:
        logger.error(
            "bot_token not set in accounts.json -> settings -> telegram -> bot_token"
        )
        sys.exit(1)
    return token


def _esc(text: str) -> str:
    """Escape HTML special characters for Telegram HTML parse mode."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def is_allowed(update: Update, config: dict) -> bool:
    """Return True if sender matches any entry in telegram.chat_ids.

    Each entry can be a numeric chat ID (int) or a @username string (with or without @).
    Empty list = allow all.
    """
    allowed = _telegram_cfg(config).get("chat_ids", [])
    if not allowed:
        return True

    user = update.effective_user
    chat_id = update.effective_chat.id
    username = (user.username or "").lower() if user else ""

    for entry in allowed:
        if isinstance(entry, int) and entry == chat_id:
            return True
        if isinstance(entry, str) and entry.lstrip("@").lower() == username:
            return True

    return False


def get_notification_chat_ids(config: dict) -> list[int]:
    """Return numeric chat IDs from telegram.chat_ids for proactive/scheduled notifications."""
    return [
        entry
        for entry in _telegram_cfg(config).get("chat_ids", [])
        if isinstance(entry, int)
    ]


def format_check_results(results: list[AccountCheckResult]) -> str:
    """Format IPO check results as an HTML Telegram message."""
    total = sum(len(r.ipos) for r in results if r.ok)
    error_count = sum(1 for r in results if r.error)
    all_failed = error_count == len(results)

    lines = ["🔍 <b>IPO Availability Check</b>", ""]

    if all_failed:
        lines.append("❌ <b>All accounts failed to check.</b>")
        lines.append("<i>Check the bot logs for details.</i>")
        return "\n".join(lines)

    if total > 0:
        lines.append(f"🚀 <b>{total} applicable IPO(s) found across all accounts</b>")
    else:
        lines.append("😴 <i>No applicable IPOs right now</i>")
    lines.append("")

    for result in results:
        lines.append(f"👤 <b>{_esc(result.name)}</b>")
        if result.error:
            lines.append(f"  ⚠️ <i>{_esc(result.error)}</i>")
        elif result.has_ipos:
            for ipo in result.ipos:
                lines.append(
                    f"  • <b>{_esc(ipo.company_name)}</b>  <code>{_esc(ipo.scrip)}</code>"
                )
        else:
            lines.append("  — Nothing right now")
        lines.append("")

    if error_count:
        lines.append(
            f"⚠️ <i>{error_count} account(s) had errors — check the bot logs.</i>"
        )

    return "\n".join(lines)


def format_apply_results(results: list[AccountApplyResult]) -> str:
    """Format IPO application results as an HTML Telegram message."""
    total_applied = sum(len(r.applied) for r in results)
    total_failed_ipos = sum(len(r.failed) for r in results)
    error_count = sum(1 for r in results if r.error)
    all_failed = error_count == len(results)

    lines = ["🚀 <b>IPO Application Results</b>", ""]

    if all_failed:
        lines.append("❌ <b>All accounts failed.</b>")
        lines.append("<i>Check the bot logs for details.</i>")
        return "\n".join(lines)

    if total_applied > 0:
        lines.append(f"🎉 <b>{total_applied} application(s) submitted successfully!</b>")
        if total_failed_ipos:
            lines.append(f"⚠️ <i>{total_failed_ipos} IPO application(s) failed</i>")
    else:
        lines.append("😴 <i>No applications were submitted</i>")
    lines.append("")

    for result in results:
        lines.append(f"👤 <b>{_esc(result.name)}</b>")
        if result.error:
            lines.append(f"  ⚠️ <i>{_esc(result.error)}</i>")
        elif result.applied or result.failed:
            for ipo in result.applied:
                lines.append(
                    f"  ✅ <b>{_esc(ipo.company_name)}</b> <code>{_esc(ipo.scrip)}</code>"
                    f" — {ipo.kitta} kitta"
                )
            for fail in result.failed:
                lines.append(f"  ❌ {_esc(fail)}")
        else:
            lines.append("  — Nothing to apply")
        lines.append("")

    if error_count:
        lines.append(
            f"⚠️ <i>{error_count} account(s) had errors — check the bot logs.</i>"
        )

    return "\n".join(lines)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — return the sender's chat ID for notification setup."""
    assert update.message is not None
    chat_id = update.effective_chat.id
    user = update.effective_user
    name = user.first_name if user else "there"
    username = f"@{user.username}" if (user and user.username) else "no username"

    logger.info("/start from %s (%s) — chat_id: %s", name, username, chat_id)

    await update.message.reply_text(
        f"👋 Hey <b>{_esc(name)}</b>!\n\n"
        f"🆔 Your chat ID is: <code>{chat_id}</code>\n\n"
        f"Add this number to <code>settings → telegram → chat_ids</code> in "
        f"<code>accounts.json</code> to receive scheduled IPO notifications.",
        parse_mode=ParseMode.HTML,
    )


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /check — check all accounts for applicable IPOs."""
    assert update.message is not None

    config = load_config()
    if not is_allowed(update, config):
        logger.warning("Unauthorized /check from chat_id=%s", update.effective_chat.id)
        return

    await update.message.reply_text("⏳ Checking all accounts for applicable IPOs…")

    if not [a for a in config["accounts"] if a.get("enabled", True)]:
        await update.message.reply_text(
            "⚠️ No enabled accounts found in <code>accounts.json</code>.",
            parse_mode=ParseMode.HTML,
        )
        return

    try:
        results = check_all_accounts(config)
        await update.message.reply_text(format_check_results(results), parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.exception("Unexpected error during /check")
        await update.message.reply_text(
            f"❌ <b>Unexpected error</b>\n\n<code>{_esc(str(e))}</code>\n\n"
            "<i>Check the bot logs for details.</i>",
            parse_mode=ParseMode.HTML,
        )


async def cmd_apply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /apply — check for IPOs then apply if any are found."""
    assert update.message is not None

    config = load_config()
    if not is_allowed(update, config):
        logger.warning("Unauthorized /apply from chat_id=%s", update.effective_chat.id)
        return

    if not [a for a in config["accounts"] if a.get("enabled", True)]:
        await update.message.reply_text(
            "⚠️ No enabled accounts found in <code>accounts.json</code>.",
            parse_mode=ParseMode.HTML,
        )
        return

    await update.message.reply_text("⏳ Checking for applicable IPOs…")

    try:
        check_results = check_all_accounts(config)
    except Exception as e:
        logger.exception("Error during pre-apply check")
        await update.message.reply_text(
            f"❌ <b>Check failed</b>\n\n<code>{_esc(str(e))}</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    total_available = sum(len(r.ipos) for r in check_results if r.ok)

    if total_available == 0:
        await update.message.reply_text(
            format_check_results(check_results), parse_mode=ParseMode.HTML
        )
        return

    await update.message.reply_text(
        f"✅ Found <b>{total_available}</b> applicable IPO(s). Applying now…",
        parse_mode=ParseMode.HTML,
    )

    try:
        apply_results = apply_all_accounts(config)
        await update.message.reply_text(
            format_apply_results(apply_results), parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.exception("Unexpected error during /apply")
        await update.message.reply_text(
            f"❌ <b>Apply failed</b>\n\n<code>{_esc(str(e))}</code>\n\n"
            "<i>Check the bot logs for details.</i>",
            parse_mode=ParseMode.HTML,
        )


async def scheduled_auto_apply(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Scheduled job: silently check for IPOs, apply if found, notify via chat ID."""
    logger.info("Scheduled auto-apply: checking for IPOs…")
    config = load_config()
    chat_ids = get_notification_chat_ids(config)

    async def notify(text: str) -> None:
        for chat_id in chat_ids:
            try:
                await context.bot.send_message(
                    chat_id=chat_id, text=text, parse_mode=ParseMode.HTML
                )
            except Exception:
                logger.exception("Failed to notify chat_id=%s", chat_id)

    try:
        check_results = check_all_accounts(config)
    except Exception as e:
        logger.exception("Scheduled auto-apply: check failed")
        await notify(
            f"⏰ <b>Scheduled check failed</b>\n\n"
            f"<code>{_esc(str(e))}</code>\n\n"
            f"<i>Check the bot logs for details.</i>"
        )
        return

    total_available = sum(len(r.ipos) for r in check_results if r.ok)

    if total_available == 0:
        logger.info("Scheduled auto-apply: no applicable IPOs found, staying silent")
        return  # Silent — no message, no spam

    logger.info("Scheduled auto-apply: found %d IPO(s), applying…", total_available)
    await notify(
        f"⏰ <b>Scheduled auto-apply triggered</b>\n\n"
        f"Found <b>{total_available}</b> applicable IPO(s). Applying now…"
    )

    try:
        apply_results = apply_all_accounts(config)
        await notify(format_apply_results(apply_results))
    except Exception as e:
        logger.exception("Scheduled auto-apply: apply failed")
        await notify(
            f"❌ <b>Auto-apply failed</b>\n\n"
            f"<code>{_esc(str(e))}</code>\n\n"
            f"<i>Check the bot logs for details.</i>"
        )


def main() -> None:
    config = load_config()
    token = get_token(config)

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(CommandHandler("apply", cmd_apply))

    # Set up scheduled auto-apply if configured
    auto_cfg = _telegram_cfg(config).get("auto_apply", {})
    if auto_cfg.get("enabled", False):
        time_str = auto_cfg.get("time", "10:00")
        tz_str = auto_cfg.get("timezone", "Asia/Kathmandu")
        hour, minute = (int(p) for p in time_str.split(":"))
        tz = zoneinfo.ZoneInfo(tz_str)
        app.job_queue.run_daily(
            scheduled_auto_apply,
            time=datetime.time(hour, minute, tzinfo=tz),
        )
        logger.info("Scheduled auto-apply enabled — daily at %s %s", time_str, tz_str)

    logger.info("Bot started — listening for commands…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

