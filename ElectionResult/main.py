#!/usr/bin/env python3
"""
Election Results TUI - Main Entry Point

A terminal-based interface for viewing Nepal election results in real-time.
Displays party-wise wins/leads, province-wise results, and constituency-level details.

Usage:
    python main.py

Features:
    - Real-time election results
    - Party-wise aggregated results
    - Province/District/Constituency navigation
    - Auto-refresh every 5 minutes
    - Persistent state (remembers last viewed location)
    - Color-coded party results
    - Keyboard shortcuts (q: quit, r: refresh, p: toggle province filter)
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from src.tui import run_tui


def main():
    """Main entry point for the application."""
    try:
        run_tui()
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nFatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
