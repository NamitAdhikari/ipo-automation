"""State management and persistence for the election TUI app."""

import json
from pathlib import Path
from typing import Optional

from .models import Location


class StateManager:
    """Manages application state and persistence."""

    def __init__(self):
        """Initialize state manager."""
        self.config_dir = Path.home() / ".config" / "election_tui"
        self.state_file = self.config_dir / "state.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def save_location(self, location: Location) -> None:
        """Save current location to disk."""
        state = {
            "province_number": location.province_number,
            "province_name": location.province_name,
            "district_name": location.district_name,
            "constituency_number": location.constituency_number,
        }

        try:
            with open(self.state_file, "w") as f:
                json.dump(state, f, indent=2)
        except Exception:
            # Silently fail if we can't save state
            pass

    def load_location(self) -> Optional[Location]:
        """Load saved location from disk."""
        if not self.state_file.exists():
            return None

        try:
            with open(self.state_file, "r") as f:
                state = json.load(f)

            location = Location(
                province_number=state.get("province_number"),
                province_name=state.get("province_name"),
                district_name=state.get("district_name"),
                constituency_number=state.get("constituency_number"),
            )

            return location
        except Exception:
            # Return None if we can't load state
            return None

    def clear_state(self) -> None:
        """Clear saved state."""
        try:
            if self.state_file.exists():
                self.state_file.unlink()
        except Exception:
            pass
