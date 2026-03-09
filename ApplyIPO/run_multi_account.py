#!/usr/bin/env python3
"""
Multi-Account IPO Application Runner
Runs the IPO application bot for multiple accounts sequentially
"""

import json
import subprocess
import sys
import time

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


def print_header():
    """Print a nice header for the application"""
    header = Text()
    header.append("🚀 ", style="bold yellow")
    header.append("Meroshare IPO Auto-Apply Bot", style="bold cyan")
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
                f"[yellow]💡 Create {config_file} based on accounts.json.example[/yellow]",
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


def run_account(account, account_num, total_accounts, settings=None):
    """Run the IPO application for a single account"""
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

    # Set environment variables for this account
    env = {
        "MEROSHARE_USERNAME": account["credentials"]["username"],
        "MEROSHARE_PASSWORD": account["credentials"]["password"],
        "MEROSHARE_DP": account["credentials"]["dp"],
        "MEROSHARE_CRN": account["credentials"]["crn"],
        "MEROSHARE_PIN": account["credentials"]["pin"],
    }

    # Add settings as environment variables
    if settings and "headless" in settings:
        env["HEADLESS"] = "true" if settings["headless"] else "false"

    # Run the main script
    try:
        result = subprocess.run(
            [sys.executable, "main_improved.py"],
            env={**subprocess.os.environ, **env},
            capture_output=False,
            text=True,
        )

        if result.returncode == 0:
            console.print()
            console.print(
                f"[bold green]✅ Account {account_num} completed successfully[/bold green]"
            )
            console.print()
            return True
        else:
            console.print()
            console.print(
                f"[bold red]❌ Account {account_num} failed with code {result.returncode}[/bold red]"
            )
            console.print()
            return False
    except Exception as e:
        console.print()
        console.print(
            f"[bold red]❌ Error running account {account_num}: {e}[/bold red]"
        )
        console.print()
        return False


def main():
    """Main function to run multi-account IPO applications"""
    console.print()
    console.print(
        Panel(
            "[bold cyan]Meroshare Multi-Account IPO Runner[/bold cyan]\n\n"
            "[white]This script will run IPO applications for all enabled accounts[/white]",
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
