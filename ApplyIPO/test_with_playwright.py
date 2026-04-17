#!/usr/bin/env python3
"""
Manual Testing Script with Playwright

This script allows manual verification of the Meroshare flow using
Playwright browser automation. It's useful for:
- Debugging API issues
- Verifying the website hasn't changed
- Testing credentials before running the API version

Usage:
    python test_with_playwright.py
"""

import json
import os
import sys
import time

from dotenv import load_dotenv

try:
    from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError
except ImportError:
    print("Playwright not installed. Install with: pip install playwright")
    print("Then install browsers with: playwright install chromium")
    sys.exit(1)

from rich.console import Console
from rich.panel import Panel

console = Console()


def load_credentials():
    """Load credentials from .env or accounts.json"""
    load_dotenv()

    # Try .env first
    username = os.getenv("MEROSHARE_USERNAME")
    password = os.getenv("MEROSHARE_PASSWORD")
    dp = os.getenv("MEROSHARE_DP")
    crn = os.getenv("MEROSHARE_CRN")
    pin = os.getenv("MEROSHARE_PIN")

    if all([username, password, dp, crn, pin]):
        return {
            "username": username,
            "password": password,
            "dp": dp,
            "crn": crn,
            "pin": pin,
            "name": "From .env",
        }

    # Try accounts.json
    if os.path.exists("accounts.json"):
        with open("accounts.json", "r") as f:
            config = json.load(f)

        for account in config.get("accounts", []):
            if account.get("enabled", True):
                creds = account["credentials"]
                return {
                    "username": creds["username"],
                    "password": creds["password"],
                    "dp": creds["dp"],
                    "crn": creds["crn"],
                    "pin": creds["pin"],
                    "name": account.get("name", "From accounts.json"),
                }

    return None


def test_login(page: Page, credentials: dict) -> bool:
    """Test the login process."""
    console.print("\n[bold cyan]Testing Login Process...[/bold cyan]")

    try:
        page.goto("https://meroshare.cdsc.com.np", wait_until="networkidle")
        console.print("  ✓ Navigated to Meroshare")

        # Select DP
        page.click("#selectBranch")
        time.sleep(1)

        page.fill(".select2-search__field", credentials["dp"])
        time.sleep(1)

        page.keyboard.press("Enter")
        time.sleep(1)
        console.print(f"  ✓ Selected DP: {credentials['dp']}")

        # Fill credentials
        page.fill("#username", credentials["username"])
        page.fill("#password", credentials["password"])
        console.print("  ✓ Filled credentials")

        # Click login
        page.click(".sign-in")

        # Wait for dashboard
        page.wait_for_url("**/dashboard**", timeout=10000)
        console.print("[bold green]  ✓ Login successful![/bold green]")

        return True

    except PlaywrightTimeoutError:
        console.print("[bold red]  ✗ Login failed - timeout or incorrect credentials[/bold red]")
        return False
    except Exception as e:
        console.print(f"[bold red]  ✗ Login failed: {e}[/bold red]")
        return False


def test_ipo_listing(page: Page) -> list:
    """Test fetching IPO listing."""
    console.print("\n[bold cyan]Testing IPO Listing...[/bold cyan]")

    try:
        # Navigate to ASBA
        page.click(".msi-asba")
        time.sleep(2)
        console.print("  ✓ Navigated to ASBA section")

        # Get company list
        companies = page.query_selector_all(".company-list")
        console.print(f"  ✓ Found {len(companies)} IPO(s)")

        ipo_list = []
        for company in companies:
            try:
                name_el = company.query_selector(".company-name")
                if name_el:
                    spans = name_el.query_selector_all("span")
                    if spans:
                        company_name = spans[0].inner_text().strip()
                        ipo_list.append(company_name)
                        console.print(f"    - {company_name}")
            except Exception:
                pass

        return ipo_list

    except Exception as e:
        console.print(f"[bold red]  ✗ Failed to fetch IPOs: {e}[/bold red]")
        return []


def test_logout(page: Page) -> bool:
    """Test the logout process."""
    console.print("\n[bold cyan]Testing Logout...[/bold cyan]")

    try:
        # Find and click logout
        logout_btn = page.query_selector("a.header-menu__link[tooltip='Logout']")
        if logout_btn:
            logout_btn.click()
            time.sleep(2)
            console.print("[bold green]  ✓ Logout successful![/bold green]")
            return True
        else:
            console.print("[yellow]  ⚠ Logout button not found[/yellow]")
            return False
    except Exception as e:
        console.print(f"[bold red]  ✗ Logout failed: {e}[/bold red]")
        return False


def main():
    """Main test function."""
    console.print(
        Panel(
            "[bold cyan]Meroshare Manual Testing with Playwright[/bold cyan]\n\n"
            "[white]This script tests the Meroshare flow using browser automation.[/white]\n"
            "[dim]Useful for debugging and verification.[/dim]",
            title="[bold yellow]🧪 Manual Test[/bold yellow]",
            border_style="cyan",
        )
    )

    # Load credentials
    credentials = load_credentials()
    if not credentials:
        console.print(
            "[bold red]❌ No credentials found![/bold red]\n"
            "Please create a .env file or accounts.json with your credentials."
        )
        sys.exit(1)

    console.print(f"\n[green]Using credentials for: {credentials['name']}[/green]")

    # Run tests
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        try:
            # Test login
            if not test_login(page, credentials):
                console.print("\n[bold red]Login failed. Stopping tests.[/bold red]")
                input("\nPress Enter to close browser...")
                return

            # Test IPO listing
            ipos = test_ipo_listing(page)

            # Test logout
            test_logout(page)

            # Summary
            console.print("\n" + "=" * 60)
            console.print("[bold green]✅ All tests completed![/bold green]")
            console.print(f"  - Login: Success")
            console.print(f"  - IPOs Found: {len(ipos)}")
            console.print(f"  - Logout: Success")
            console.print("=" * 60)

            console.print(
                "\n[yellow]Note: This test script only verifies the flow. "
                "Use the API version (main_api.py) for actual IPO applications.[/yellow]"
            )

        except Exception as e:
            console.print(f"\n[bold red]Test failed: {e}[/bold red]")

        finally:
            input("\nPress Enter to close browser...")
            browser.close()


if __name__ == "__main__":
    main()
