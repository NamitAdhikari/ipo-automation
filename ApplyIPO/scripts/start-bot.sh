#!/usr/bin/env bash
# start-bot.sh — Shell wrapper used by launchd (macOS) and systemd (Linux).
#
# Edit PROJECT_DIR to the absolute path of your ApplyIPO folder.
# The script activates the venv and runs bot.py from the correct directory.

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"

cd "$PROJECT_DIR" || exit 1
exec "$PROJECT_DIR/.venv/bin/python3" "$PROJECT_DIR/bot.py"
