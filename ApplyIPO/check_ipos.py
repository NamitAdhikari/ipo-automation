#!/usr/bin/env python3
"""
IPO Availability Checker

Checks whether any applicable IPOs are open for application across all configured
accounts. Does NOT apply — only reports what's available.

Exit codes:
  0 — no applicable IPOs found (nothing to do)
  1 — applicable IPOs exist (consider running run_accounts.py)
  2 — fatal error (missing config, all accounts failed to check, etc.)

Example cron usage:
  python check_ipos.py && echo "No IPOs" || python run_accounts.py
"""

import json
import sys
from dataclasses import dataclass, field

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from meroshare import (
    IPOIssue,
    MeroshareAPIError,
    MeroshareIPOApplicator,
)

console = Console()


@dataclass
class AccountCheckResult:
    """Result of checking a single account for applicable IPOs."""
    name: str
    ipos: list[IPOIssue] = field(default_factory=list)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None

    @property
    def has_ipos(self) -> bool:
        return self.ok and len(self.ipos) > 0


def load_accounts(config_file: str = "accounts.json") -> dict:
    with open(config_file) as f:
        return json.load(f)


def check_account(account: dict) -> AccountCheckResult:
    """
    Login and fetch applicable IPOs for a single account.
    Returns an AccountCheckResult (with ipos list or error string).
    """
    name = account.get("name", "Unnamed")
    credentials = account["credentials"]

    applicator = MeroshareIPOApplicator(
        username=credentials["username"],
        password=credentials["password"],
        dp_code=credentials["dp"],
        crn=credentials["crn"],
        pin=credentials["pin"],
    )

    try:
        eligible_dps = applicator.find_matching_dps()
        if not eligible_dps:
            return AccountCheckResult(name=name, error=f"No DP found matching '{credentials['dp']}'")

        applicator.login(capital=eligible_dps[0])

        issues = applicator.get_applicable_ipos()

        # Same filter as apply scripts: ordinary shares only
        filtered = [i for i in issues if i.share_group.lower() == "ordinary shares"]

        skipped = [i for i in issues if i.share_group.lower() != "ordinary shares"]
        for s in skipped:
            console.print(f"  [dim]⚠ Skipping {s.company_name} ({s.share_group})[/dim]")

        return AccountCheckResult(name=name, ipos=filtered)

    except MeroshareAPIError as e:
        return AccountCheckResult(name=name, error=str(e))
    finally:
        try:
            applicator.close()
        except Exception:
            pass


def check_all_accounts(config: dict) -> list[AccountCheckResult]:
    """
    Check all enabled accounts and return a list of AccountCheckResult.
    Intended for reuse by bot.py and other callers.
    """
    enabled = [a for a in config["accounts"] if a.get("enabled", True)]
    results = []
    for account in enabled:
        name = account.get("name", "Unnamed")
        console.print(f"[bold white]Account:[/bold white] [cyan]{name}[/cyan]")
        result = check_account(account)
        results.append(result)

        if result.error:
            console.print(f"  [red]❌ Error: {result.error}[/red]")
        elif result.has_ipos:
            console.print(f"  [bold green]✅ {len(result.ipos)} applicable IPO(s):[/bold green]")
            for ipo in result.ipos:
                console.print(f"    • [bold white]{ipo.company_name}[/bold white] [dim]({ipo.scrip})[/dim]")
        else:
            console.print("  [yellow]— No applicable IPOs[/yellow]")
        console.print()

    return results


def main():
    console.print()
    console.print(
        Panel(
            "[bold cyan]Meroshare IPO Availability Checker[/bold cyan]\n\n"
            "[white]Checks all configured accounts for open, applicable IPOs[/white]\n"
            "[dim]Does not apply — check only[/dim]",
            title="[bold yellow]🔍 IPO Check[/bold yellow]",
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print()

    try:
        config = load_accounts()
    except FileNotFoundError as e:
        console.print(
            Panel(
                f"[red]❌ Config file not found: {e.filename}[/red]\n\n"
                "[yellow]💡 Create it based on accounts.sample.json[/yellow]",
                title="[bold red]Error[/bold red]",
                border_style="red",
            )
        )
        sys.exit(2)
    except json.JSONDecodeError as e:
        console.print(
            Panel(
                f"[red]❌ Invalid JSON in accounts.json[/red]\n\n[yellow]{e}[/yellow]",
                title="[bold red]JSON Error[/bold red]",
                border_style="red",
            )
        )
        sys.exit(2)
    enabled_accounts = [a for a in config["accounts"] if a.get("enabled", True)]

    if not enabled_accounts:
        console.print("[bold red]❌ No enabled accounts found in accounts.json[/bold red]")
        console.print()
        sys.exit(2)

    console.print(f"[bold green]→ Checking {len(enabled_accounts)} account(s)...[/bold green]")
    console.print()

    results = check_all_accounts(config)

    # Summary table
    console.print(f"[bold magenta]{'═' * 55}[/bold magenta]")
    console.print("[bold yellow]📊 SUMMARY[/bold yellow]")
    console.print(f"[bold magenta]{'═' * 55}[/bold magenta]")
    console.print()

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="cyan", width=4)
    table.add_column("Account", style="white")
    table.add_column("Status", style="green")
    table.add_column("Applicable IPOs", style="yellow")

    total_ipos = 0
    errors = 0

    for idx, result in enumerate(results, 1):
        if result.error:
            status = "[red]Error[/red]"
            ipo_names = "[dim]—[/dim]"
            errors += 1
        elif result.has_ipos:
            status = "[bold green]Found[/bold green]"
            ipo_names = ", ".join(i.scrip for i in result.ipos)
            total_ipos += len(result.ipos)
        else:
            status = "[yellow]None[/yellow]"
            ipo_names = "[dim]—[/dim]"

        table.add_row(str(idx), result.name, status, ipo_names)

    console.print(table)
    console.print()

    accounts_checked = len(results) - errors
    accounts_with_ipos = sum(1 for r in results if r.has_ipos)

    console.print(
        f"[bold cyan]Accounts checked:[/bold cyan] {accounts_checked}/{len(results)}  |  "
        f"[bold green]With IPOs:[/bold green] {accounts_with_ipos}  |  "
        f"[bold yellow]Total IPOs:[/bold yellow] {total_ipos}"
    )
    console.print()

    # Determine exit code
    if errors > 0 and accounts_checked == 0:
        console.print("[bold red]❌ All accounts failed to check.[/bold red]")
        console.print()
        sys.exit(2)

    if total_ipos > 0:
        console.print(
            f"[bold green]✅ {total_ipos} applicable IPO(s) available — consider running run_accounts.py[/bold green]"
        )
        console.print()
        sys.exit(1)  # Signal: action needed

    console.print("[bold yellow]— No applicable IPOs found across all accounts.[/bold yellow]")
    console.print()
    sys.exit(0)


if __name__ == "__main__":
    main()
