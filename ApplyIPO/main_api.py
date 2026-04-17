#!/usr/bin/env python3
"""
Meroshare IPO Auto-Apply Bot (API Version)

This script automatically applies for IPOs on Meroshare using REST API calls
instead of browser automation. It's faster, more reliable, and doesn't require
a browser to be installed.
"""

import atexit
import os
import signal
import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from meroshare_api import (
    Capital,
    IPOIssue,
    MeroshareAPIError,
    MeroshareIPOApplicator,
)

load_dotenv()
console = Console()


def print_section(title: str, emoji: str = "📌"):
    """Print a section separator"""
    console.print()
    console.print(f"[bold magenta]{'─' * 60}[/bold magenta]")
    console.print(f"[bold yellow]{emoji} {title}[/bold yellow]")
    console.print(f"[bold magenta]{'─' * 60}[/bold magenta]")
    console.print()


# Load credentials from environment
MEROSHARE_USERNAME = os.getenv("MEROSHARE_USERNAME")
MEROSHARE_PASSWORD = os.getenv("MEROSHARE_PASSWORD")
MEROSHARE_DP = os.getenv("MEROSHARE_DP")
MEROSHARE_CRN = os.getenv("MEROSHARE_CRN")
MEROSHARE_PIN = os.getenv("MEROSHARE_PIN")

if not (
    MEROSHARE_USERNAME
    and MEROSHARE_PASSWORD
    and MEROSHARE_DP
    and MEROSHARE_CRN
    and MEROSHARE_PIN
):
    console.print()
    console.print(
        Panel(
            "[red]❌ Missing credentials!\n\n"
            "Please set the following in your .env file:\n"
            "• MEROSHARE_USERNAME\n"
            "• MEROSHARE_PASSWORD\n"
            "• MEROSHARE_DP\n"
            "• MEROSHARE_CRN\n"
            "• MEROSHARE_PIN",
            title="[bold red]Configuration Error[/bold red]",
            border_style="red",
        )
    )
    console.print()
    sys.exit(1)

# Initialize the IPO applicator
console.print("[dim]✓ Initializing Meroshare API client...[/dim]")

applicator = MeroshareIPOApplicator(
    username=MEROSHARE_USERNAME,
    password=MEROSHARE_PASSWORD,
    dp_code=MEROSHARE_DP,
    crn=MEROSHARE_CRN,
    pin=MEROSHARE_PIN,
)

# Register cleanup
atexit.register(lambda: applicator.close())


def get_input_with_timeout(timeout: int = 4) -> str:
    """Get user input with a timeout. Cross-platform compatible."""
    import platform
    import sys
    import threading

    result = ["n"]  # Default value

    def read_input():
        try:
            user_input = input().strip().lower()
            result[0] = user_input
        except EOFError:
            pass  # Handle piped input gracefully

    if platform.system() == "Windows":
        # Windows: Use threading-based timeout
        input_thread = threading.Thread(target=read_input, daemon=True)
        input_thread.start()
        input_thread.join(timeout=timeout)
        return result[0]
    else:
        # Unix/Linux/Mac: Use signal-based timeout
        def _raise(signum, frame):
            raise TimeoutError("Input timeout")

        signal.signal(signal.SIGALRM, _raise)
        signal.alarm(timeout)
        try:
            return input().strip().lower()
        except (TimeoutError, Exception):
            return "n"
        finally:
            signal.alarm(0)


def select_dp(eligible_dps: list[Capital]) -> Capital:
    """Let user select from multiple matching DPs."""
    console.print("[bold green]📋 Available DPs:[/bold green]\n")

    for idx, dp in enumerate(eligible_dps, start=1):
        console.print(f"  [bold cyan]{idx}.[/bold cyan] [white]{dp.code} - {dp.name}[/white]")

    console.print()
    console.print(
        f"[yellow]Warning: Multiple DPs found matching '{MEROSHARE_DP}'. "
        "Please select the correct one from the list above.[/yellow]"
    )

    while True:
        try:
            choice = int(input("Enter the number corresponding to your DP choice: "))
            if 1 <= choice <= len(eligible_dps):
                selected = eligible_dps[choice - 1]
                console.print(
                    f"\n[green]✓ Selected DP:[/green] [bold white]{selected.code} - {selected.name}[/bold white]\n"
                )
                return selected
            else:
                console.print("[red]❌ Invalid choice. Please enter a valid number.[/red]")
        except ValueError:
            console.print("[red]❌ Invalid input. Please enter a number.[/red]")


def display_company_info(issue: IPOIssue):
    """Display company information in a nice panel."""
    console.print()
    console.print(
        Panel(
            f"[bold white]{issue.company_name}[/bold white]\n\n"
            f"[cyan]Scrip:[/cyan] {issue.scrip}\n"
            f"[cyan]Share Type:[/cyan] {issue.share_type}\n"
            f"[cyan]Share Group:[/cyan] {issue.share_group}",
            title="[bold green]🏢 Company Found[/bold green]",
            border_style="green",
        )
    )
    console.print()


def apply_ipo(issue: IPOIssue) -> bool:
    """Apply for an IPO."""
    display_company_info(issue)

    try:
        # Get issue details for min kitta
        details = applicator._client.get_issue_details(issue.company_share_id)
        min_kitta = details.get("minUnit", issue.min_unit)

        console.print(f"[green]  ✓ Minimum Quantity:[/green] [bold white]{min_kitta}[/bold white] shares")

        # Display bank info
        if applicator.bank_info:
            console.print(f"[green]  ✓ Bank:[/green] [white]{applicator.bank_info.get('bank_name', 'N/A')}[/white]")
            console.print(
                f"[green]  ✓ Account:[/green] [white]{applicator.bank_info.get('account_number', 'N/A')}[/white]"
            )

        console.print(f"[green]  ✓ Applied Kitta:[/green] [white]{min_kitta}[/white]")
        console.print(f"[green]  ✓ CRN:[/green] [white]{MEROSHARE_CRN}[/white]")
        console.print("[green]  ✓ Transaction PIN entered[/green]")

        # Apply for IPO
        result = applicator.apply_ipo(issue, kitta=min_kitta)

        console.print()
        console.print(
            Panel(
                f"[bold green]✅ Application Submitted![/bold green]\n\n"
                f"[white]Company:[/white] [bold cyan]{issue.company_name}[/bold cyan]\n"
                f"[white]Shares:[/white] [bold cyan]{min_kitta}[/bold cyan]\n"
                f"[white]Status:[/white] [bold green]{result.get('status', 'SUCCESS')}[/bold green]",
                border_style="yellow",
            )
        )
        console.print()

        return True

    except MeroshareAPIError as e:
        console.print()
        console.print(f"[bold red]❌ Application failed: {e}[/bold red]")
        console.print()
        return False


def main():
    """Main function to run the IPO application bot."""
    print_section("LOGIN PROCESS", "🔐")

    try:
        # Find matching DPs
        eligible_dps = applicator.find_matching_dps()

        if not eligible_dps:
            console.print()
            console.print(f"[red]❌ Error: No eligible DP found for '{MEROSHARE_DP}'[/red]")
            console.print("[yellow]💡 Hint: Check your MEROSHARE_DP in .env file[/yellow]")
            console.print()
            sys.exit(1)

        # Select DP if multiple matches
        if len(eligible_dps) > 1:
            selected_dp = select_dp(eligible_dps)
        else:
            selected_dp = eligible_dps[0]
            console.print(f"[green]✓ Selected DP: {selected_dp.code} - {selected_dp.name}[/green]\n")

        # Login
        console.print("[dim]Logging in...[/dim]")
        applicator.login(capital=selected_dp)

        console.print()
        console.print("[bold green]✅ Login successful![/bold green]")
        console.print()

    except MeroshareAPIError as e:
        console.print()
        console.print(f"[bold red]❌ Login failed: {e}[/bold red]")
        console.print("[yellow]💡 Please check your credentials and try again[/yellow]")
        console.print()
        sys.exit(1)

    print_section("IPO APPLICATION", "📝")

    # Main application loop
    applied = 0

    while True:
        try:
            # Fetch applicable IPOs
            issues = applicator.get_applicable_ipos()

            # Filter to ordinary shares only
            filtered_issues = []
            for issue in issues:
                if issue.share_group.lower() != "ordinary shares":
                    console.print(
                        f"[yellow]⚠ Skipping {issue.company_name} - "
                        f"Unsupported share type: {issue.share_group}[/yellow]"
                    )
                    console.print()
                    continue
                filtered_issues.append(issue)

            if not filtered_issues and applied == 0:
                console.print()
                console.print("[bold red]❌ No companies found![/bold red]")
                console.print("[yellow]💡 There may be no IPOs available right now[/yellow]")
                console.print()
                sys.exit(1)
            elif not filtered_issues and applied > 0:
                console.print()
                console.print(
                    f"[bold green]✅ All done! Applied to {applied} company/companies[/bold green]"
                )
                console.print()
                break

            # Process first available IPO
            issue = filtered_issues[0]

            if applied > 0:
                console.print()
                console.print(
                    f"[bold cyan]📊 Progress: {applied} application(s) completed[/bold cyan]"
                )
                console.print()
                console.print(
                    "  [yellow]Continue to the next company? (y/N):[/yellow] ",
                    end="",
                )
                choice = get_input_with_timeout()
                if choice != "y":
                    console.print()
                    console.print("[yellow]👋 Stopping as requested[/yellow]")
                    console.print()
                    break

            success = apply_ipo(issue)
            if not success:
                break

            applied += 1
            console.print(
                Panel(
                    f"[bold green]✅ Application #{applied} Complete![/bold green]",
                    style="bold green",
                )
            )

        except MeroshareAPIError as e:
            console.print()
            console.print(f"[bold red]❌ Error: {e}[/bold red]")
            console.print()
            break

    print_section("SUMMARY", "📊")
    console.print(
        Panel(
            f"[bold cyan]Total Applications:[/bold cyan] [bold white]{applied}[/bold white]\n\n"
            f"[green]✅ Script completed successfully![/green]",
            title="[bold green]🎉 All Done![/bold green]",
            border_style="green",
        )
    )
    console.print()


if __name__ == "__main__":
    main()
