#!/usr/bin/env python3
"""
Multi-Account IPO Application Runner (API Version)

Runs the IPO application bot for multiple accounts sequentially using
the REST API instead of browser automation.
"""

import json
import sys
import time

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from meroshare_api import (
    Capital,
    IPOIssue,
    MeroshareAPIError,
    MeroshareIPOApplicator,
)

console = Console()


def print_header():
    """Print a nice header for the application"""
    header = Text()
    header.append("🚀 ", style="bold yellow")
    header.append("Meroshare IPO Auto-Apply Bot (API)", style="bold cyan")
    header.append(" 🚀", style="bold yellow")

    console.print()
    console.print(Panel(header, style="bold blue", padding=(1, 2)))
    console.print()


def load_accounts(config_file="accounts.json"):
    """Load account configurations from JSON file"""
    try:
        with open(config_file, "r") as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        console.print()
        console.print(
            Panel(
                f"[red]❌ Configuration file not found: {config_file}[/red]\n\n"
                f"[yellow]💡 Create {config_file} based on accounts.sample.json[/yellow]",
                title="[bold red]Error[/bold red]",
                border_style="red",
            )
        )
        console.print()
        sys.exit(1)
    except json.JSONDecodeError as e:
        console.print()
        console.print(
            Panel(
                f"[red]❌ Invalid JSON in {config_file}[/red]\n\n"
                f"[yellow]Error: {e}[/yellow]",
                title="[bold red]JSON Error[/bold red]",
                border_style="red",
            )
        )
        console.print()
        sys.exit(1)


def print_account_summary(config):
    """Print a summary of all accounts"""
    console.print()
    console.print("[bold cyan]📋 Account Summary[/bold cyan]")
    console.print()

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="cyan", width=6)
    table.add_column("Account Name", style="white")
    table.add_column("DP", style="yellow")
    table.add_column("Status", style="green")

    enabled_count = 0
    for idx, account in enumerate(config["accounts"], 1):
        status = "✓ Enabled" if account["enabled"] else "✗ Disabled"
        status_color = "green" if account["enabled"] else "red"

        table.add_row(
            str(idx),
            account.get("name", "Unnamed"),
            account["credentials"]["dp"],
            f"[{status_color}]{status}[/{status_color}]",
        )

        if account["enabled"]:
            enabled_count += 1

    console.print(table)
    console.print()
    console.print(f"[bold green]→ {enabled_count} account(s) enabled[/bold green]")
    console.print()


def select_dp(eligible_dps: list[Capital], dp_code: str, account_name: str) -> Capital:
    """Select DP - auto-select if only one, otherwise prompt user."""
    if len(eligible_dps) == 1:
        return eligible_dps[0]

    console.print(f"[bold green]📋 Available DPs for {account_name}:[/bold green]\n")

    for idx, dp in enumerate(eligible_dps, start=1):
        console.print(f"  [bold cyan]{idx}.[/bold cyan] [white]{dp.code} - {dp.name}[/white]")

    console.print()
    console.print(
        f"[yellow]Warning: Multiple DPs found matching '{dp_code}'. "
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


def apply_single_ipo(applicator: MeroshareIPOApplicator, issue: IPOIssue, crn: str) -> bool:
    """Apply for a single IPO."""
    console.print()
    console.print(
        Panel(
            f"[bold white]{issue.company_name}[/bold white]\n\n"
            f"[cyan]Scrip:[/cyan] {issue.scrip}\n"
            f"[cyan]Share Type:[/cyan] {issue.share_type}\n"
            f"[cyan]Share Group:[/cyan] {issue.share_group}",
            title="[bold green]🏢 Applying to Company[/bold green]",
            border_style="green",
        )
    )
    console.print()

    try:
        # Get issue details for min kitta
        details = applicator._client.get_issue_details(issue.company_share_id)
        min_kitta = details.get("minUnit", issue.min_unit)

        console.print(f"[green]  ✓ Minimum Quantity:[/green] [bold white]{min_kitta}[/bold white] shares")

        if applicator.bank_info:
            console.print(f"[green]  ✓ Bank:[/green] [white]{applicator.bank_info.get('bank_name', 'N/A')}[/white]")
            console.print(
                f"[green]  ✓ Account:[/green] [white]{applicator.bank_info.get('account_number', 'N/A')}[/white]"
            )

        console.print(f"[green]  ✓ Applied Kitta:[/green] [white]{min_kitta}[/white]")
        console.print(f"[green]  ✓ CRN:[/green] [white]{crn}[/white]")
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


def run_account(account, account_num, total_accounts, settings=None) -> bool:
    """Run the IPO application for a single account using API"""
    console.print()
    console.print(
        Panel(
            f"[bold white]{account.get('name', 'Unnamed Account')}[/bold white]\n\n"
            f"[cyan]Username:[/cyan] {account['credentials']['username']}\n"
            f"[cyan]DP:[/cyan] {account['credentials']['dp']}",
            title=f"[bold yellow]🏃 Running Account {account_num}/{total_accounts}[/bold yellow]",
            border_style="yellow",
        )
    )
    console.print()

    credentials = account["credentials"]

    applicator = MeroshareIPOApplicator(
        username=credentials["username"],
        password=credentials["password"],
        dp_code=credentials["dp"],
        crn=credentials["crn"],
        pin=credentials["pin"],
    )

    try:
        # Find matching DPs
        eligible_dps = applicator.find_matching_dps()

        if not eligible_dps:
            console.print(f"[red]❌ No DP found matching '{credentials['dp']}'[/red]")
            return False

        # Select DP
        selected_dp = select_dp(eligible_dps, credentials["dp"], account.get("name", "Account"))

        # Login
        console.print("[dim]Logging in...[/dim]")
        applicator.login(capital=selected_dp)
        console.print("[green]✓ Login successful![/green]")
        console.print()

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
                continue
            filtered_issues.append(issue)

        if not filtered_issues:
            console.print("[yellow]⚠ No applicable IPOs found for this account[/yellow]")
            console.print()
            return True  # Not a failure, just no IPOs available

        # Apply to all available IPOs
        applied = 0
        failed = 0
        for issue in filtered_issues:
            success = apply_single_ipo(applicator, issue, credentials["crn"])
            if success:
                applied += 1
            else:
                failed += 1
                console.print(f"[yellow]⚠ Failed to apply for {issue.company_name}, continuing...[/yellow]")

        console.print()
        if applied > 0:
            console.print(f"[bold green]✅ Applied to {applied} IPO(s) for {account.get('name', 'Account')}[/bold green]")
        else:
            console.print(f"[bold red]❌ Failed to apply to any IPOs for {account.get('name', 'Account')}[/bold red]")
        if failed > 0:
            console.print(f"[yellow]⚠ {failed} application(s) failed[/yellow]")
        console.print()

        # Return True only if at least one application succeeded
        return applied > 0

    except MeroshareAPIError as e:
        console.print()
        console.print(f"[bold red]❌ Error for {account.get('name', 'Unknown')}: {e}[/bold red]")
        console.print()
        return False
    finally:
        try:
            applicator.close()
        except Exception:
            pass


def main():
    """Main function to run multi-account IPO applications"""
    console.print()
    console.print(
        Panel(
            "[bold cyan]Meroshare Multi-Account IPO Runner (API Version)[/bold cyan]\n\n"
            "[white]This script will run IPO applications for all enabled accounts[/white]\n"
            "[dim]Using REST API - No browser required![/dim]",
            title="[bold yellow]🚀 Multi-Account Mode[/bold yellow]",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    # Load configuration
    config = load_accounts()

    # Print summary
    print_account_summary(config)

    # Get enabled accounts
    enabled_accounts = [acc for acc in config["accounts"] if acc.get("enabled", True)]

    if not enabled_accounts:
        console.print("[bold red]❌ No enabled accounts found![/bold red]")
        console.print()
        sys.exit(1)

    console.print()
    console.print(
        "[bold green]🚀 Starting IPO applications for enabled accounts...[/bold green]"
    )
    console.print()

    # Run each enabled account
    results = []
    global_settings = config.get("settings", {})
    wait_between = global_settings.get("wait_between_accounts_seconds", 5)
    continue_on_error = global_settings.get("continue_on_account_failure", True)

    for idx, account in enumerate(enabled_accounts, 1):
        success = run_account(account, idx, len(enabled_accounts), global_settings)
        results.append(
            {
                "name": account.get("name", "Unnamed"),
                "success": success,
            }
        )

        # Wait between accounts (except after the last one)
        if idx < len(enabled_accounts):
            if not success and not continue_on_error:
                console.print()
                console.print("[bold red]❌ Stopping due to account failure[/bold red]")
                console.print()
                break

            console.print(
                f"[dim]⏳ Waiting {wait_between} seconds before next account...[/dim]"
            )
            time.sleep(wait_between)

    # Print final summary
    console.print()
    console.print(f"[bold magenta]{'═' * 60}[/bold magenta]")
    console.print("[bold yellow]📊 FINAL SUMMARY[/bold yellow]")
    console.print(f"[bold magenta]{'═' * 60}[/bold magenta]")
    console.print()

    summary_table = Table(show_header=True, header_style="bold magenta")
    summary_table.add_column("#", style="cyan", width=6)
    summary_table.add_column("Account Name", style="white")
    summary_table.add_column("Result", style="green")

    successful = 0
    for idx, result in enumerate(results, 1):
        status = "✅ Success" if result["success"] else "❌ Failed"
        status_color = "green" if result["success"] else "red"
        summary_table.add_row(
            str(idx),
            result["name"],
            f"[{status_color}]{status}[/{status_color}]",
        )
        if result["success"]:
            successful += 1

    console.print(summary_table)
    console.print()
    console.print(
        f"[bold cyan]Total:[/bold cyan] {len(results)} accounts | "
        f"[bold green]Success:[/bold green] {successful} | "
        f"[bold red]Failed:[/bold red] {len(results) - successful}"
    )
    console.print()


if __name__ == "__main__":
    main()
