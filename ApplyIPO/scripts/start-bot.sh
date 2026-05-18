#!/usr/bin/env bash
# start-bot.sh — Shell wrapper used by launchd (macOS) and systemd (Linux).
# PROJECT_DIR is resolved automatically from the script's location.

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"

cd "$PROJECT_DIR" || exit 1
exec "$PROJECT_DIR/.venv/bin/python3" "$PROJECT_DIR/bot.py"
