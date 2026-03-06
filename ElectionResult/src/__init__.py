"""Election Results TUI - A terminal-based interface for viewing Nepal election results."""

from .models import (
    CandidateResult,
    ConstituencyResult,
    ElectionData,
    Location,
    PartyResult,
    ProvincePartyResult,
    ResultStatus,
)
from .scraper import ElectionScraper
from .state import StateManager
from .tui import ElectionTUI, run_tui

__all__ = [
    "CandidateResult",
    "ConstituencyResult",
    "ElectionData",
    "ElectionScraper",
    "ElectionTUI",
    "Location",
    "PartyResult",
    "ProvincePartyResult",
    "ResultStatus",
    "StateManager",
    "run_tui",
]

__version__ = "1.0.0"
