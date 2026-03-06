"""Main TUI application for election results display."""

import threading
from pathlib import Path
from typing import Dict, List, Optional

from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.reactive import reactive
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Label,
    Select,
    Static,
)

from .models import (
    QUICK_CARDS,
    ConstituencyResult,
    ElectionData,
    Location,
    get_total_seats,
)
from .scraper import ElectionScraper
from .state import StateManager


class Breadcrumb(Static):
    """Display current location breadcrumb."""

    breadcrumb = reactive("")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update_breadcrumb("Home")

    def update_breadcrumb(self, breadcrumb: str) -> None:
        """Update the breadcrumb text."""
        self.breadcrumb = breadcrumb
        self.update(f"📍 {breadcrumb}")

    def on_mount(self) -> None:
        """Handle mount event."""
        self.styles.background = "darkblue"
        self.styles.color = "white"
        self.styles.padding = (0, 1)
        self.styles.text_style = "bold"


class StatusBar(Static):
    """Display status and last update time."""

    status_text = reactive("")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def update_status(self, text: str) -> None:
        """Update status text."""
        self.status_text = text
        self.update(text)

    def on_mount(self) -> None:
        """Handle mount event."""
        self.styles.background = "darkgreen"
        self.styles.color = "white"
        self.styles.padding = (0, 1)


class Notification(Static):
    """Toast notification widget."""

    def __init__(self, message: str, *args, **kwargs):
        super().__init__(message, *args, **kwargs)
        self.message = message

    def on_mount(self) -> None:
        """Handle mount event."""
        self.styles.background = "red"
        self.styles.color = "white"
        self.styles.padding = (1, 2)
        self.styles.border = ("heavy", "white")
        self.styles.width = "50%"
        self.styles.height = "auto"

        # Auto-dismiss after 5 seconds
        self.set_timer(5, self.dismiss_notification)

    def dismiss_notification(self) -> None:
        """Dismiss the notification."""
        self.remove()


class NavigationPanel(Container):
    """Panel for province/district/constituency selection."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.province_select: Optional[Select] = None
        self.district_select: Optional[Select] = None
        self.constituency_select: Optional[Select] = None

    def compose(self) -> ComposeResult:
        """Compose the navigation panel."""
        yield Label("📋 Navigation", classes="panel-title")

        # Province selector
        self.province_select = Select(
            [("Select Province", "0")],
            prompt="Province",
            id="province_select",
            allow_blank=False,
        )
        yield self.province_select

        # District selector
        self.district_select = Select(
            [("Select District", "")],
            prompt="District",
            id="district_select",
            allow_blank=False,
        )
        self.district_select.disabled = True
        yield self.district_select

        # Constituency selector
        self.constituency_select = Select(
            [("Select Constituency", "0")],
            prompt="Constituency",
            id="constituency_select",
            allow_blank=False,
        )
        self.constituency_select.disabled = True
        yield self.constituency_select

        # Province filter toggle
        yield Label("", id="province_filter_label")

    def on_mount(self) -> None:
        """Handle mount event."""
        self.styles.background = "darkgray"
        self.styles.padding = 1
        self.styles.border = ("heavy", "blue")
        self.styles.width = 40
        self.styles.height = "100%"


class ResultsPanel(VerticalScroll):
    """Panel for displaying election results."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        """Compose the results panel."""
        yield Label("📊 Election Results", classes="panel-title", id="results_title")
        yield DataTable(id="results_table", zebra_stripes=True)

    def on_mount(self) -> None:
        """Handle mount event."""
        self.styles.background = "darkgray"
        self.styles.padding = 1
        self.styles.border = ("heavy", "green")
        self.styles.width = "1fr"
        self.styles.height = "100%"


class QuickCardWidget(Container):
    """Widget for displaying a single quick card."""

    def __init__(
        self, card, result: Optional[ConstituencyResult] = None, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.card = card
        self.result = result
        self.add_class("quick-card")

    def compose(self) -> ComposeResult:
        """Compose the quick card."""
        # Title
        yield Label(
            f"{self.card.name} - P{self.card.province_number}/{self.card.district_name}/C{self.card.constituency_number}",
            classes="quick-card-title",
        )

        # Results table
        table = DataTable(classes="quick-card-table", zebra_stripes=True)
        table.add_column("Rank", width=6)
        table.add_column("Party", width=15)
        table.add_column("Candidate", width=25)
        table.add_column("Votes", width=10)
        table.add_column("Status", width=8)

        if self.result and self.result.candidates:
            for candidate in self.result.candidates[:3]:  # Top 3 candidates
                status_text = Text(candidate.status.value)
                if candidate.status.value == "Win":
                    status_text.stylize("bold green")
                elif candidate.status.value == "Lead":
                    status_text.stylize("bold yellow")

                table.add_row(
                    str(candidate.rank),
                    candidate.party_name,
                    candidate.candidate_name,
                    f"{candidate.votes:,}",
                    status_text,
                )
        else:
            table.add_row("--", "No data", "--", "--", "--")

        yield table


class QuickCardsPanel(Container):
    """Panel for displaying quick constituency cards."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        """Compose the quick cards panel."""
        yield Label(
            "⚡ Quick Cards (8 Constituencies)",
            classes="panel-title",
            id="quick_cards_title",
        )
        # Create 4 rows for the cards
        for i in range(4):
            yield Horizontal(classes="quick-cards-row", id=f"quick_cards_row_{i}")

    def on_mount(self) -> None:
        """Handle mount event."""
        self.styles.background = "darkgray"
        self.styles.padding = 1
        self.styles.border = ("heavy", "yellow")
        self.styles.height = "100%"


class ElectionTUI(App):
    """Main TUI application for election results."""

    CSS = """
    Screen {
        background: black;
    }

    .panel-title {
        background: darkcyan;
        color: white;
        text-style: bold;
        padding: 0 1;
        margin-bottom: 1;
    }

    DataTable {
        height: 1fr;
    }

    Select {
        margin: 1 0;
    }

    Label {
        width: 100%;
    }

    .quick-card {
        border: solid green;
        background: #111111;
        padding: 1;
        margin: 1;
        height: auto;
        width: 48%;
    }

    .quick-card-title {
        background: green;
        color: white;
        text-style: bold;
        padding: 0 1;
        margin-bottom: 1;
    }

    .quick-card-table {
        height: auto;
        max-height: 10;
    }

    #quick_cards_panel {
        height: 100%;
    }

    .quick-cards-row {
        height: 25%;
        width: 100%;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "manual_refresh", "Refresh"),
        ("p", "toggle_province_filter", "Toggle Province Filter"),
        ("c", "toggle_quick_cards", "Toggle Quick Cards"),
        ("h", "go_home", "Go to Homepage"),
    ]

    def __init__(self):
        super().__init__()
        self.scraper = ElectionScraper()
        self.state_manager = StateManager()
        self.election_data: Optional[ElectionData] = None
        self.current_location = Location()
        self.auto_refresh_timer: Optional[threading.Timer] = None
        self.time_until_refresh = 300  # 5 minutes in seconds
        self.show_province_filter = False
        self.filtered_province: Optional[int] = None
        self.is_loading = False
        self.is_restoring = False  # Flag to prevent event handlers during restoration
        self.show_quick_cards = False
        self.quick_cards_data: Dict[str, Optional[ConstituencyResult]] = {}

        # Setup file logging for debugging
        self.debug_log = Path("/tmp/tui_debug.log")
        with open(self.debug_log, "w") as f:
            f.write("=== TUI Debug Log ===\n")

    def compose(self) -> ComposeResult:
        """Compose the application layout."""
        yield Header(show_clock=True)
        yield Breadcrumb(id="breadcrumb")
        yield StatusBar(id="status_bar")

        with Horizontal():
            yield NavigationPanel(id="nav_panel")
            yield ResultsPanel(id="results_panel")
            yield QuickCardsPanel(id="quick_cards_panel")

        yield Footer()

    def on_mount(self) -> None:
        """Handle mount event."""
        self.log("=" * 60)
        self.log("[MOUNT] on_mount starting")
        self._debug("[MOUNT] on_mount starting")

        # Load saved location
        saved_location = self.state_manager.load_location()
        self.log(f"[MOUNT] Loaded location: {saved_location}")
        self._debug(f"[MOUNT] Loaded location: {saved_location}")
        if saved_location:
            self.current_location = saved_location
            self.log(f"[MOUNT] Current location set to: {self.current_location}")
            self._debug(f"[MOUNT] Current location set to: {self.current_location}")

        # Initialize province selector
        self.log("[MOUNT] Calling populate_provinces")
        self.populate_provinces()

        # Start initial data load
        self.log("[MOUNT] Calling load_data")
        self.load_data()

        # Hide quick cards panel initially
        self.query_one("#quick_cards_panel").display = False

        # Load quick cards data
        self.load_quick_cards()

        # Start auto-refresh timer
        self.start_auto_refresh()

        # Update timer display
        self.set_interval(1, self.update_timer_display)

        # Update breadcrumb with restored location
        if saved_location and saved_location.province_number:
            self.log("[MOUNT] Updating breadcrumb")
            self.update_breadcrumb()

        self.log("[MOUNT] on_mount complete")
        self.log("=" * 60)

    def populate_provinces(self) -> None:
        """Populate province selector."""
        self.log("[POPULATE] populate_provinces starting")
        provinces = self.scraper.get_provinces()
        options = [("All Provinces", "0")] + [
            (f"Province {num} - {name}", str(num)) for num, name in provinces
        ]
        self.log(f"[POPULATE] Province options: {options}")

        nav_panel = self.query_one("#nav_panel", NavigationPanel)
        if nav_panel.province_select:
            self.log("[POPULATE] Setting province options")
            nav_panel.province_select.set_options(options)

            # Restore saved province if exists
            if self.current_location.province_number:
                self.log(
                    f"[POPULATE] Restoring province: {self.current_location.province_number}"
                )
                # Set flag to prevent event handler from clearing district/constituency
                self.is_restoring = True
                self.log(f"[POPULATE] is_restoring set to: {self.is_restoring}")
                nav_panel.province_select.value = str(
                    self.current_location.province_number
                )
                self.log(
                    f"[POPULATE] Province value set to: {nav_panel.province_select.value}"
                )
                # Load districts for saved province without saving state again
                # Schedule restoration after UI is fully mounted
                self.log("[POPULATE] Scheduling restore_saved_selections for 0.5s")
                self.set_timer(0.5, self.restore_saved_selections)

        self.log("[POPULATE] populate_provinces complete")

    @on(Select.Changed, "#province_select")
    def on_province_change(self, event: Select.Changed) -> None:
        """Handle province selection change."""
        self.log(
            f"[EVENT] on_province_change fired - value: {event.value}, is_restoring: {self.is_restoring}"
        )
        # Skip if we're restoring state
        if self.is_restoring:
            self.log("[EVENT] Skipping province change - is_restoring is True")
            return

        if event.value == "0":
            self.log("[EVENT] Province set to 'All Provinces'")
            self.current_location.province_number = None
            self.current_location.province_name = None
            self.current_location.district_name = None
            self.current_location.constituency_number = None
            self.update_breadcrumb()
            return

        province_num = int(event.value)
        self.log(f"[EVENT] Processing province selection: {province_num}")
        self.on_province_selected(province_num)

    def on_province_selected(self, province_num: int) -> None:
        """Handle province selection."""
        provinces = dict(self.scraper.get_provinces())
        province_name = provinces.get(province_num, f"Province {province_num}")

        self.current_location.province_number = province_num
        self.current_location.province_name = province_name
        self.current_location.district_name = None
        self.current_location.constituency_number = None

        self.update_breadcrumb()
        self.state_manager.save_location(self.current_location)

        # Reset district and constituency selectors
        nav_panel = self.query_one("#nav_panel", NavigationPanel)
        nav_panel.district_select.disabled = True
        nav_panel.constituency_select.disabled = True

        # Load districts for this province
        self.load_districts(province_num)

    @work(thread=True)
    def load_districts(self, province_num: int) -> None:
        """Load districts for selected province."""
        districts = self.scraper.get_districts_for_province(province_num)
        self.call_from_thread(self.populate_districts, districts)

    def populate_districts(self, districts: List[str]) -> None:
        """Populate district selector."""
        nav_panel = self.query_one("#nav_panel", NavigationPanel)

        if not districts:
            nav_panel.district_select.disabled = True
            return

        options = [("Select District", "")] + [(d, d) for d in districts]
        nav_panel.district_select.set_options(options)
        nav_panel.district_select.disabled = False

        # Don't auto-restore here - let restore_saved_selections handle it

    @on(Select.Changed, "#district_select")
    def on_district_change(self, event: Select.Changed) -> None:
        """Handle district selection change."""
        self.log(
            f"[EVENT] on_district_change fired - value: {event.value}, is_restoring: {self.is_restoring}"
        )
        # Skip if we're restoring state
        if self.is_restoring:
            self.log("[EVENT] Skipping district change - is_restoring is True")
            return

        if not event.value:
            self.log("[EVENT] Skipping district change - value is empty")
            return

        self.log(f"[EVENT] Processing district selection: {event.value}")
        self.on_district_selected(str(event.value))

    def on_district_selected(self, district_name: str) -> None:
        """Handle district selection."""
        self.current_location.district_name = district_name
        self.current_location.constituency_number = None

        self.update_breadcrumb()
        self.state_manager.save_location(self.current_location)

        # Reset constituency selector
        nav_panel = self.query_one("#nav_panel", NavigationPanel)
        nav_panel.constituency_select.disabled = True

        # Load constituencies for this district
        self.load_constituencies(self.current_location.province_number, district_name)

    @work(thread=True)
    def load_constituencies(self, province_num: int, district_name: str) -> None:
        """Load constituencies for selected district."""
        constituencies = self.scraper.get_constituencies_for_district(
            province_num, district_name
        )
        self.call_from_thread(self.populate_constituencies, constituencies)

    def populate_constituencies(self, constituencies: List[int]) -> None:
        """Populate constituency selector."""
        self.log("[POPULATE_CONST] populate_constituencies called")
        self.log(f"[POPULATE_CONST] Constituencies: {constituencies}")
        self.log(f"[POPULATE_CONST] is_restoring: {self.is_restoring}")
        self._debug(
            f"[POPULATE_CONST] populate_constituencies called with: {constituencies}"
        )

        nav_panel = self.query_one("#nav_panel", NavigationPanel)

        if not constituencies:
            self.log("[POPULATE_CONST] No constituencies, disabling dropdown")
            nav_panel.constituency_select.disabled = True
            return

        options = [("Select Constituency", "0")] + [
            (f"Constituency {c}", str(c)) for c in constituencies
        ]
        self.log(f"[POPULATE_CONST] Setting options: {options}")
        self.log(
            f"[POPULATE_CONST] Current value before set_options: {nav_panel.constituency_select.value}"
        )
        nav_panel.constituency_select.set_options(options)
        self.log(
            f"[POPULATE_CONST] Current value after set_options: {nav_panel.constituency_select.value}"
        )
        nav_panel.constituency_select.disabled = False
        self.log("[POPULATE_CONST] Dropdown enabled")
        self._debug(
            f"[POPULATE_CONST] Options set, value after set_options: {nav_panel.constituency_select.value}"
        )

        # Don't auto-restore here - let restore_saved_selections handle it

    @on(Select.Changed, "#constituency_select")
    def on_constituency_change(self, event: Select.Changed) -> None:
        """Handle constituency selection change."""
        self.log(
            f"[EVENT] on_constituency_change fired - value: {event.value}, is_restoring: {self.is_restoring}"
        )
        # Skip if we're restoring state
        if self.is_restoring:
            self.log("[EVENT] Skipping constituency change - is_restoring is True")
            return

        if event.value == "0":
            self.log("[EVENT] Skipping constituency change - value is 0")
            return

        constituency_num = int(event.value)
        self.log(f"[EVENT] Processing constituency selection: {constituency_num}")
        self.on_constituency_selected(constituency_num)

    def on_constituency_selected(self, constituency_num: int) -> None:
        """Handle constituency selection."""
        self.current_location.constituency_number = constituency_num
        self.update_breadcrumb()
        self.state_manager.save_location(self.current_location)

        # Refresh data to show constituency results
        self.load_data()

    def update_breadcrumb(self) -> None:
        """Update breadcrumb display."""
        breadcrumb = self.query_one("#breadcrumb", Breadcrumb)
        breadcrumb.update_breadcrumb(self.current_location.get_breadcrumb())

    @work(thread=True)
    def load_data(self) -> None:
        """Load election data from the website."""
        if self.is_loading:
            return

        self.is_loading = True
        self.call_from_thread(self.show_loading_status)

        try:
            # Always load homepage data
            self.election_data = self.scraper.scrape_homepage()

            # If complete location is selected, load constituency data
            if self.current_location.is_complete():
                const_result = self.scraper.scrape_constituency(self.current_location)
                if const_result:
                    self.election_data.constituency_result = const_result

            # If province is selected, load province data
            if (
                self.current_location.province_number
                and not self.current_location.is_complete()
            ):
                province_results = self.scraper.scrape_province_results(
                    self.current_location.province_number
                )
                self.election_data.province_party_results[
                    self.current_location.province_number
                ] = province_results

            self.call_from_thread(self.update_display)
            self.call_from_thread(
                self.update_status, f"Last updated: {self.election_data.last_updated}"
            )

        except Exception as e:
            self.call_from_thread(self.show_error, f"Error loading data: {str(e)}")

        finally:
            self.is_loading = False

    def show_loading_status(self) -> None:
        """Show loading status."""
        status_bar = self.query_one("#status_bar", StatusBar)
        status_bar.update_status("⏳ Loading data...")

    def update_status(self, message: str) -> None:
        """Update status bar."""
        status_bar = self.query_one("#status_bar", StatusBar)
        refresh_time = self.time_until_refresh
        status_bar.update_status(f"{message} | Next refresh in: {refresh_time}s")

    def show_error(self, message: str) -> None:
        """Show error notification."""
        notification = Notification(f"⚠️  {message}")
        self.mount(notification)

        # Update status to show stale data warning
        status_bar = self.query_one("#status_bar", StatusBar)
        refresh_time = self.time_until_refresh
        status_bar.update_status(
            f"⚠️ Using stale data | Next refresh in: {refresh_time}s"
        )

    def update_display(self) -> None:
        """Update the results display."""
        if not self.election_data:
            return

        table = self.query_one("#results_table", DataTable)
        table.clear(columns=True)

        # Show constituency results if available
        if self.election_data.constituency_result:
            self.display_constituency_results(table)
        # Show province results if province is selected
        elif self.current_location.province_number:
            self.display_province_results(table)
        # Show overall party results
        else:
            self.display_party_results(table)

    def display_party_results(self, table: DataTable) -> None:
        """Display overall party-wise results."""
        results_title = self.query_one("#results_title", Label)
        results_title.update("📊 Party-wise Results (All Provinces)")

        table.add_columns("Rank", "Party", "Win", "Lead", "Total")

        results = self.election_data.party_results
        if self.show_province_filter and self.filtered_province:
            # Filter by province
            province_results = self.election_data.province_party_results.get(
                self.filtered_province, []
            )
            if province_results:
                results = [
                    type(
                        "PartyResult",
                        (),
                        {
                            "party_name": pr.party_name,
                            "win_count": pr.win_count,
                            "lead_count": pr.lead_count,
                            "total": pr.total,
                            "color": pr.color,
                        },
                    )()
                    for pr in province_results
                ]

        # Calculate totals for seats summary
        total_declared = sum(party.win_count for party in results)
        total_leading = sum(party.lead_count for party in results)
        total_seats = get_total_seats()  # Total parliamentary seats in Nepal
        remaining = total_seats - total_declared - total_leading

        for idx, party in enumerate(results, 1):
            table.add_row(
                str(idx),
                Text(party.party_name, style=f"bold {party.color}"),
                str(party.win_count),
                str(party.lead_count),
                str(party.total),
            )

        # Add separator and summary row
        table.add_row("─" * 4, "─" * 20, "─" * 5, "─" * 5, "─" * 5)
        table.add_row(
            "",
            Text("📊 SEATS SUMMARY", style="bold cyan"),
            Text(f"{total_declared}", style="bold green"),
            Text(f"{total_leading}", style="bold yellow"),
            Text(f"{total_declared + total_leading}", style="bold white"),
        )
        table.add_row(
            "",
            Text("Remaining Seats", style="italic"),
            "",
            "",
            Text(f"{remaining}", style="italic dim"),
        )

    def display_province_results(self, table: DataTable) -> None:
        """Display province-wise party results."""
        results_title = self.query_one("#results_title", Label)
        results_title.update(
            f"📊 Party Results - {self.current_location.province_name}"
        )

        table.add_columns("Rank", "Party", "Win", "Lead", "Total")

        province_results = self.election_data.province_party_results.get(
            self.current_location.province_number, []
        )

        for idx, party in enumerate(province_results, 1):
            table.add_row(
                str(idx),
                Text(party.party_name, style=f"bold {party.color}"),
                str(party.win_count),
                str(party.lead_count),
                str(party.total),
            )

    def display_constituency_results(self, table: DataTable) -> None:
        """Display constituency-level candidate results."""
        const_result = self.election_data.constituency_result

        results_title = self.query_one("#results_title", Label)
        results_title.update(
            f"📊 Constituency Results - {const_result.district_name}, "
            f"Constituency {const_result.constituency_number}"
        )

        table.add_columns("Rank", "Party", "Candidate", "Votes", "Status")

        for candidate in const_result.candidates:
            status_style = "bold green" if candidate.status.value == "Win" else "yellow"
            table.add_row(
                str(candidate.rank),
                Text(candidate.party_name, style=f"bold {candidate.color}"),
                candidate.candidate_name,
                f"{candidate.votes:,}",
                Text(candidate.status.value, style=status_style),
            )

    def start_auto_refresh(self) -> None:
        """Start auto-refresh timer."""
        self.time_until_refresh = 300  # 5 minutes

        def auto_refresh():
            if self.show_quick_cards:
                self.app.call_from_thread(self.load_quick_cards)
            else:
                self.app.call_from_thread(self.load_data)
            self.app.call_from_thread(self.start_auto_refresh)

        self.auto_refresh_timer = threading.Timer(300, auto_refresh)
        self.auto_refresh_timer.daemon = True
        self.auto_refresh_timer.start()

    def update_timer_display(self) -> None:
        """Update the countdown timer display."""
        if self.time_until_refresh > 0:
            self.time_until_refresh -= 1

        if self.election_data:
            self.update_status(f"Last updated: {self.election_data.last_updated}")

    def action_manual_refresh(self) -> None:
        """Handle manual refresh action."""
        # Cancel existing timer
        if self.auto_refresh_timer:
            self.auto_refresh_timer.cancel()

        # Start new refresh
        if self.show_quick_cards:
            self.load_quick_cards()
            self.update_status("Quick Cards refreshing...")
        else:
            self.load_data()
        self.start_auto_refresh()

    def action_toggle_province_filter(self) -> None:
        """Toggle province filter for party results."""
        if not self.current_location.province_number:
            self.show_error("Please select a province first to use province filter")
            return

        self.show_province_filter = not self.show_province_filter

        if self.show_province_filter:
            self.filtered_province = self.current_location.province_number
            # Load province data if not already loaded
            if self.filtered_province not in self.election_data.province_party_results:
                self.load_province_data(self.filtered_province)
            else:
                self.update_display()
        else:
            self.filtered_province = None
            self.update_display()

    @work(thread=True)
    def load_province_data(self, province_num: int) -> None:
        """Load province-level data."""
        try:
            province_results = self.scraper.scrape_province_results(province_num)
            self.election_data.province_party_results[province_num] = province_results
            self.call_from_thread(self.update_display)
        except Exception as e:
            self.call_from_thread(self.show_error, f"Error loading province data: {e}")

    @work(thread=True)
    def load_quick_cards(self) -> None:
        """Load data for all quick cards."""

        for card in QUICK_CARDS:
            try:
                location = card.to_location()
                result = self.scraper.scrape_constituency(location)
                self.quick_cards_data[card.name] = result
            except Exception as e:
                self.log(f"Error loading quick card {card.name}: {e}")
                self.quick_cards_data[card.name] = None

        self.call_from_thread(self.update_quick_cards_display)

    def update_quick_cards_display(self) -> None:
        """Update the quick cards panel with latest data."""

        # Update each row with 2 cards
        for row_idx in range(4):
            row = self.query_one(f"#quick_cards_row_{row_idx}", Horizontal)
            row.remove_children()

            card_idx = row_idx * 2

            # First card in row
            if card_idx < len(QUICK_CARDS):
                result = self.quick_cards_data.get(QUICK_CARDS[card_idx].name)
                card_widget = QuickCardWidget(QUICK_CARDS[card_idx], result)
                row.mount(card_widget)

            # Second card in row
            if card_idx + 1 < len(QUICK_CARDS):
                result = self.quick_cards_data.get(QUICK_CARDS[card_idx + 1].name)
                card_widget = QuickCardWidget(QUICK_CARDS[card_idx + 1], result)
                row.mount(card_widget)

        self.update_status(f"Quick Cards updated - {len(QUICK_CARDS)} constituencies")

    def action_toggle_quick_cards(self) -> None:
        """Toggle quick cards view."""
        self.show_quick_cards = not self.show_quick_cards

        nav_panel = self.query_one("#nav_panel", NavigationPanel)
        results_panel = self.query_one("#results_panel", ResultsPanel)
        quick_cards_panel = self.query_one("#quick_cards_panel", QuickCardsPanel)

        if self.show_quick_cards:
            # Show quick cards, hide navigation and regular results
            nav_panel.display = False
            results_panel.display = False
            quick_cards_panel.display = True
            self.update_status("Quick Cards View - Press 'c' to return")
        else:
            # Show navigation and regular results, hide quick cards
            nav_panel.display = True
            results_panel.display = True
            quick_cards_panel.display = False
            self.update_status("Normal View")

    def action_go_home(self) -> None:
        """Go back to homepage party stats view."""
        # Clear current location
        self.current_location = Location()

        # Reset navigation panel
        nav_panel = self.query_one("#nav_panel", NavigationPanel)
        nav_panel.province_select.value = "0"
        nav_panel.district_select.disabled = True
        nav_panel.constituency_select.disabled = True

        # Update breadcrumb
        breadcrumb = self.query_one("#breadcrumb", Breadcrumb)
        breadcrumb.update_breadcrumb("Home")

        # Clear saved state
        self.state_manager.clear_state()

        # Reload data to show homepage stats
        self.load_data()

        self.update_status("Homepage - Party-wise results (All Provinces)")

    def _debug(self, msg: str) -> None:
        """Write debug message to file."""
        try:
            with open(self.debug_log, "a") as f:
                f.write(f"{msg}\n")
                f.flush()
        except Exception:
            pass

    def restore_saved_selections(self) -> None:
        """Restore saved district and constituency selections."""
        self.log("=" * 60)
        self.log("[RESTORE] Starting restore_saved_selections")
        self.log(f"[RESTORE] Current location: {self.current_location}")
        self._debug("=" * 60)
        self._debug("[RESTORE] Starting restore_saved_selections")
        self._debug(f"[RESTORE] Current location: {self.current_location}")

        if not self.current_location.province_number:
            self.log("[RESTORE] No province number, exiting")
            return

        # Set flag to prevent event handlers from firing
        self.is_restoring = True
        self.log(f"[RESTORE] is_restoring flag set to: {self.is_restoring}")

        # Flag to indicate if we scheduled a callback that will clear is_restoring
        callback_scheduled = False

        try:
            nav_panel = self.query_one("#nav_panel", NavigationPanel)
            self.log(f"[RESTORE] Got nav_panel: {nav_panel}")

            # Load districts for the saved province
            self.log(
                f"[RESTORE] Loading districts for province {self.current_location.province_number}"
            )
            districts = self.scraper.get_districts_for_province(
                self.current_location.province_number
            )

            if not districts:
                self.log("[RESTORE] No districts found, exiting")
                return

            # Populate district dropdown
            self.log(f"[RESTORE] Found {len(districts)} districts: {districts}")
            options = [("Select District", "")] + [(d, d) for d in districts]
            self.log(f"[RESTORE] District options: {options}")
            nav_panel.district_select.set_options(options)
            nav_panel.district_select.disabled = False
            self.log("[RESTORE] District dropdown enabled")

            # If district was saved, restore it
            self.log(
                f"[RESTORE] Checking if district saved: {self.current_location.district_name}"
            )
            self.log(
                f"[RESTORE] District in list: {self.current_location.district_name in districts}"
            )

            if (
                self.current_location.district_name
                and self.current_location.district_name in districts
            ):
                self.log(
                    f"[RESTORE] Setting district: {self.current_location.district_name}"
                )
                nav_panel.district_select.value = self.current_location.district_name
                self.log(
                    f"[RESTORE] District value set to: {nav_panel.district_select.value}"
                )

                # Load constituencies for the saved district
                self.log(
                    f"[RESTORE] Loading constituencies for {self.current_location.province_number}/{self.current_location.district_name}"
                )
                constituencies = self.scraper.get_constituencies_for_district(
                    self.current_location.province_number,
                    self.current_location.district_name,
                )

                self.log(f"[RESTORE] Constituencies loaded: {constituencies}")
                self.log(f"[RESTORE] Constituencies type: {type(constituencies)}")
                self._debug(f"[RESTORE] Constituencies loaded: {constituencies}")
                self._debug(f"[RESTORE] Constituencies type: {type(constituencies)}")

                if constituencies:
                    # Populate constituency dropdown
                    const_options = [("Select Constituency", "0")] + [
                        (f"Constituency {c}", str(c)) for c in constituencies
                    ]
                    self.log(f"[RESTORE] Constituency options created: {const_options}")
                    self.log(
                        f"[RESTORE] Setting options on constituency_select: {nav_panel.constituency_select}"
                    )
                    nav_panel.constituency_select.set_options(const_options)
                    self.log("[RESTORE] Options set successfully")
                    nav_panel.constituency_select.disabled = False
                    self.log("[RESTORE] Constituency dropdown enabled")

                    # If constituency was saved, restore it
                    self.log(
                        f"[RESTORE] Saved constituency number: {self.current_location.constituency_number}"
                    )
                    self.log(
                        f"[RESTORE] Constituency in list check: {self.current_location.constituency_number in constituencies}"
                    )
                    self._debug(
                        f"[RESTORE] Saved constituency number: {self.current_location.constituency_number}"
                    )
                    self._debug(
                        f"[RESTORE] Constituency in list check: {self.current_location.constituency_number in constituencies}"
                    )

                    if (
                        self.current_location.constituency_number
                        and self.current_location.constituency_number in constituencies
                    ):
                        constituency_value = str(
                            self.current_location.constituency_number
                        )
                        self.log(
                            f"[RESTORE] Will set constituency value to: '{constituency_value}' (type: {type(constituency_value)})"
                        )
                        self.log(
                            f"[RESTORE] Current constituency value before: {nav_panel.constituency_select.value}"
                        )
                        self._debug(
                            f"[RESTORE] Will set constituency value to: '{constituency_value}' (type: {type(constituency_value)})"
                        )
                        self._debug(
                            f"[RESTORE] Current constituency value before: {nav_panel.constituency_select.value}"
                        )

                        # Use set_timer with 0.1 second delay to ensure value is set after UI fully updates
                        def set_constituency_value():
                            self.log("[RESTORE] Inside set_constituency_value callback")
                            # Re-query nav_panel to ensure we have valid reference
                            panel = self.query_one("#nav_panel", NavigationPanel)
                            self.log(
                                f"[RESTORE] constituency_select widget: {panel.constituency_select}"
                            )
                            self.log(
                                f"[RESTORE] constituency_select.value before: {panel.constituency_select.value}"
                            )
                            self.log(
                                f"[RESTORE] Setting value to: '{constituency_value}'"
                            )
                            panel.constituency_select.value = constituency_value
                            self.log(
                                f"[RESTORE] Constituency value AFTER setting: {panel.constituency_select.value}"
                            )
                            self._debug(
                                f"[RESTORE] Constituency value AFTER setting: {panel.constituency_select.value}"
                            )
                            # Trigger data load for the complete location
                            self.log("[RESTORE] Calling load_data()")
                            self.load_data()
                            self.log(
                                "[RESTORE] set_constituency_value callback complete"
                            )

                            # Clear flag after setting value
                            self.log("[RESTORE] Clearing is_restoring flag in callback")
                            self.log(
                                f"[RESTORE] is_restoring before clear: {self.is_restoring}"
                            )
                            self.is_restoring = False
                            self.log(
                                f"[RESTORE] is_restoring after clear: {self.is_restoring}"
                            )
                            self.log("=" * 60)

                        self.log(
                            "[RESTORE] Scheduling set_constituency_value with set_timer 0.1s"
                        )
                        self._debug(
                            "[RESTORE] Scheduling set_constituency_value with set_timer 0.1s"
                        )
                        self.set_timer(0.1, set_constituency_value)
                        self.log("[RESTORE] set_timer scheduled")
                        self._debug("[RESTORE] set_timer scheduled")
                        callback_scheduled = (
                            True  # Mark that callback will clear the flag
                        )
                    else:
                        self.log(
                            f"[RESTORE] Constituency {self.current_location.constituency_number} not in list: {constituencies}"
                        )
                        self.log(
                            f"[RESTORE] Condition check - number is None: {self.current_location.constituency_number is None}"
                        )
                        self.log(
                            f"[RESTORE] Condition check - in list: {self.current_location.constituency_number in constituencies if self.current_location.constituency_number else 'N/A'}"
                        )
                else:
                    self.log("[RESTORE] No constituencies found (empty list)")
            else:
                self.log(
                    f"[RESTORE] District not being restored - saved: {self.current_location.district_name}, in list: {self.current_location.district_name in districts if self.current_location.district_name else 'N/A'}"
                )
        finally:
            # Clear flag only if we didn't schedule a callback to do it
            if not callback_scheduled and self.is_restoring:
                self.log("[RESTORE] Clearing is_restoring flag in finally")
                self.is_restoring = False
            elif callback_scheduled:
                self.log(
                    "[RESTORE] Skipping flag clear in finally - callback will handle it"
                )

    def action_quit(self) -> None:
        """Handle quit action."""
        if self.auto_refresh_timer:
            self.auto_refresh_timer.cancel()
        self.exit()


def run_tui():
    """Run the TUI application."""
    app = ElectionTUI()
    app.run()
