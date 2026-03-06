import atexit
import os
import signal
import time
from typing import TYPE_CHECKING

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

if TYPE_CHECKING:
    from selenium.webdriver.chrome.webdriver import WebDriver as WebDriverChrome
    from selenium.webdriver.remote.webelement import WebElement


load_dotenv()
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


def print_section(title: str, emoji: str = "📌"):
    """Print a section separator"""
    console.print()
    console.print(f"[bold magenta]{'─' * 60}[/bold magenta]")
    console.print(f"[bold yellow]{emoji} {title}[/bold yellow]")
    console.print(f"[bold magenta]{'─' * 60}[/bold magenta]")
    console.print()


print_header()

MEROSHARE_USERNAME = os.getenv("MEROSHARE_USERNAME")
MEROSHARE_PASSWORD = os.getenv("MEROSHARE_PASSWORD")
MEROSHARE_DP = os.getenv("MEROSHARE_DP")
MEROSHARE_CRN = os.getenv("MEROSHARE_CRN")
MEROSHARE_PIN = os.getenv("MEROSHARE_PIN")
HEADLESS_MODE = os.getenv("HEADLESS", "false").lower() == "true"

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
    exit(1)

console.print("[dim]✓ Credentials loaded successfully[/dim]")

console.print("[dim]✓ Initializing browser...[/dim]")

chrome_options = ChromeOptions()
if HEADLESS_MODE:
    chrome_options.add_argument("--headless=new")

driver: "WebDriverChrome" = Chrome(options=chrome_options, headless=HEADLESS_MODE)  # type: ignore
driver.maximize_window()

atexit.register(lambda: driver.quit())

wait = WebDriverWait(driver, 5)

print_section("LOGIN PROCESS", "🔐")

console.print("[cyan]→[/cyan] Opening Meroshare website...")
driver.get("https://meroshare.cdsc.com.np")
console.print("[green]✓[/green] Website loaded\n")

console.print("[cyan]→[/cyan] Opening DP selector...")
selector = wait.until(EC.presence_of_element_located((By.ID, "selectBranch")))
selector.click()

selectable = wait.until(
    EC.presence_of_element_located((By.CSS_SELECTOR, ".select2-hidden-accessible"))
)
options = selectable.find_elements(By.CSS_SELECTOR, "option")


searchable = wait.until(
    EC.presence_of_element_located((By.CSS_SELECTOR, ".select2-search__field"))
)
searchable.send_keys(MEROSHARE_DP)

search_results = wait.until(
    EC.presence_of_element_located((By.CSS_SELECTOR, ".select2-results__options"))
)
eligible_options = search_results.find_elements(
    By.CSS_SELECTOR, ".select2-results__option"
)

eligible_dps = {}
console.print("[bold green]📋 Available DPs:[/bold green]\n")

for idx, li_elem in enumerate(eligible_options, start=1):
    eligible_dps[idx] = li_elem
    console.print(
        f"  [bold cyan]{idx}.[/bold cyan] [white]{li_elem.text.strip()}[/white]"
    )

console.print()

if not eligible_dps:
    console.print()
    console.print(f"[red]❌ Error: No eligible DP found for '{MEROSHARE_DP}'[/red]")
    console.print("[yellow]💡 Hint: Check your MEROSHARE_DP in .env file[/yellow]")
    console.print()
    exit(1)

if len(eligible_dps) > 1:
    console.print(
        f"[yellow]Warning: Multiple DPs found matching '{MEROSHARE_DP}'. Please select the correct one from the list above.[/yellow]"
    )
    while True:
        try:
            choice = int(input("Enter the number corresponding to your DP choice: "))
            if 1 <= choice <= len(eligible_dps):
                selectable_dp = list(eligible_dps.values())[choice - 1]
                console.print(
                    f"\n[green]✓ Selected DP:[/green] [bold white]{selectable_dp.text}[/bold white]\n"
                )
                selectable_dp.click()
                break
            else:
                console.print(
                    "[red]❌ Invalid choice. Please enter a valid number.[/red]"
                )
        except ValueError:
            console.print("[red]❌ Invalid input. Please enter a number.[/red]")
else:
    eligible_dps[1].click()
    console.print("[green]✓ Selected DP[/green]\n")

# Click somewhere else to close the dropdown
wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".copyright"))).click()

console.print("[cyan]→[/cyan] Filling credentials...")
username_input = wait.until(EC.presence_of_element_located((By.ID, "username")))
username_input.send_keys(MEROSHARE_USERNAME)

password_input = wait.until(EC.presence_of_element_located((By.ID, "password")))
password_input.send_keys(MEROSHARE_PASSWORD)
console.print("[green]✓[/green] Credentials entered\n")

console.print("[cyan]→[/cyan] Logging in...")
login_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".sign-in")))
login_button.click()

try:
    wait.until(EC.url_contains("/dashboard"))
    console.print()
    console.print("[bold green]✅ Login successful![/bold green]")
    console.print()
except TimeoutException:
    console.print()
    console.print("[bold red]❌ Login failed![/bold red]")
    console.print("[yellow]💡 Please check your credentials and try again[/yellow]")
    console.print()
    exit(1)

print_section("IPO APPLICATION", "📝")

console.print("[cyan]→[/cyan] Navigating to ASBA application page...")


def navigate_to_asba():
    asba_menu = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".msi-asba")))
    asba_menu.click()


navigate_to_asba()
console.print("[green]✓[/green] ASBA page loaded\n")


def fetch_companies():
    companies = wait.until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".company-list"))
    )
    filtered_companies = []
    for company in companies:
        try:
            available_action = company.find_element(
                By.CSS_SELECTOR, ".action-buttons"
            ).text
            if "Apply" in available_action:
                filtered_companies.append(company)
        except Exception as e:
            console.print(f"[red]Error processing a company element: {e}[/red]")
    return filtered_companies


def find_min_kitta_smart(section_blocks: list) -> str | None:
    """
    Find minimum kitta by searching for "Minimum Quantity" in the entire column text.
    """
    console.print("[dim]  → Searching for minimum quantity...[/dim]")

    # Search for column containing "Minimum Quantity" text
    for section in section_blocks:
        try:
            col_divs = section.find_elements(By.CSS_SELECTOR, ".col-md-4")

            for col in col_divs:
                try:
                    # Get the entire text of this column
                    col_text = col.text.strip()
                    col_text_lower = col_text.lower()

                    # Check if this column contains "Minimum Quantity"
                    # Using various possible phrasings
                    if any(
                        phrase in col_text_lower
                        for phrase in [
                            "minimum quantity",
                            "min. quantity",
                            "min quantity",
                        ]
                    ):
                        # Now extract the value from this column
                        try:
                            form_value = col.find_element(
                                By.CSS_SELECTOR, ".form-value"
                            )
                            value_span = form_value.find_element(By.TAG_NAME, "span")
                            value_text = value_span.text.strip()

                            # Validate it's a reasonable number
                            if value_text.isdigit():
                                console.print(
                                    f"[green]  ✓ Minimum Quantity:[/green] [bold white]{value_text}[/bold white] shares"
                                )
                                return value_text
                        except Exception:
                            # Maybe the value is directly in the column text
                            # Extract number from the column text
                            import re

                            numbers = re.findall(r"\b\d+\b", col_text)
                            for num in numbers:
                                if 1 <= int(num) <= 10000:  # Reasonable kitta range
                                    console.print(
                                        f"[green]  ✓ Minimum Quantity:[/green] [bold white]{num}[/bold white] shares"
                                    )
                                    return num
                except Exception:
                    continue
        except Exception:
            continue

    # Fallback to old index-based method
    console.print(
        "[yellow]  ⚠ Using fallback method to find minimum quantity...[/yellow]"
    )
    try:
        if len(section_blocks) > 1:
            min_kitta_main_div = section_blocks[1]
            col_divs = min_kitta_main_div.find_elements(By.CSS_SELECTOR, ".col-md-4")
            if len(col_divs) > 5:
                min_kitta_div = col_divs[5]
                min_kitta_form_div = min_kitta_div.find_element(
                    By.CSS_SELECTOR, ".form-value"
                )
                min_kitta = min_kitta_form_div.find_element(
                    By.TAG_NAME, "span"
                ).text.strip()
                console.print(
                    f"[yellow]  ⚠ Minimum Quantity:[/yellow] [bold white]{min_kitta}[/bold white] shares (via fallback)"
                )
                return min_kitta
    except Exception as e:
        console.print(f"[red]  ❌ Fallback method failed: {e}[/red]")

    return None


def apply_ipo(company: "WebElement"):
    company_detail = company.find_element(By.CSS_SELECTOR, ".company-name")
    spans = company_detail.find_elements(By.TAG_NAME, "span")

    company_name, *_, share_type, share_group = [span.text.strip() for span in spans]

    console.print()
    console.print(
        Panel(
            f"[bold white]{company_name}[/bold white]\n\n"
            f"[cyan]Share Type:[/cyan] {share_type}\n"
            f"[cyan]Share Group:[/cyan] {share_group}",
            title="[bold green]🏢 Company Found[/bold green]",
            border_style="green",
        )
    )
    console.print()

    apply_btn = company.find_element(By.CSS_SELECTOR, ".btn-issue")
    apply_btn.click()

    # Scroll down to the bottom of the page to load all elements
    container = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".card-body"))
    )
    driver.execute_script("window.scrollTo(0, arguments[0].scrollHeight);", container)
    time.sleep(1)  # Give time for dynamic content to load

    # Find minimum kitta using smart content-based method
    section_blocks = wait.until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".section-block"))
    )

    min_kitta = find_min_kitta_smart(section_blocks)

    if not min_kitta:
        console.print()
        console.print(
            "[bold red]❌ Error: Could not find minimum kitta value![/bold red]"
        )
        console.print(
            "[yellow]💡 Hint: The website structure may have changed[/yellow]"
        )
        console.print()
        return False

    # Fill in the application form
    # Bank Select
    banks_select = wait.until(EC.presence_of_element_located((By.ID, "selectBank")))
    bank_options = banks_select.find_elements(By.TAG_NAME, "option")

    # Filter out placeholder option (usually "Please choose one")
    valid_bank_options = [opt for opt in bank_options if opt.get_attribute("value")]

    if len(valid_bank_options) == 1:
        valid_bank_options[0].click()
        console.print(
            f"[green]  ✓ Bank:[/green] [white]{valid_bank_options[0].text}[/white]"
        )
    elif len(valid_bank_options) > 1:
        console.print("[yellow]  ⚠ Multiple banks found, selecting first[/yellow]")
        valid_bank_options[0].click()
    else:
        console.print("[red]  ❌ No valid bank options found![/red]")
        return False

    # Account Number Fill
    account_number_select = wait.until(
        EC.presence_of_element_located((By.ID, "accountNumber"))
    )
    # API Call happens here, so introduce a wait to ensure options are loaded
    time.sleep(1)
    account_number_options = account_number_select.find_elements(By.TAG_NAME, "option")

    # Filter out placeholder
    valid_account_options = [
        opt for opt in account_number_options if opt.get_attribute("value")
    ]

    if len(valid_account_options) == 1:
        valid_account_options[0].click()
        console.print(
            f"[green]  ✓ Account:[/green] [white]{valid_account_options[0].text}[/white]"
        )
    elif len(valid_account_options) > 1:
        console.print("[yellow]  ⚠ Multiple accounts found, selecting first[/yellow]")
        valid_account_options[0].click()
    else:
        console.print("[red]  ❌ No valid account options found![/red]")
        return False

    # Kitta Fill
    kitta_input = wait.until(EC.presence_of_element_located((By.ID, "appliedKitta")))
    kitta_input.send_keys(min_kitta)
    console.print(f"[green]  ✓ Applied Kitta:[/green] [white]{min_kitta}[/white]")

    # CRN Fill
    crn_input = wait.until(EC.presence_of_element_located((By.ID, "crnNumber")))
    crn_input.send_keys(MEROSHARE_CRN)
    console.print(f"[green]  ✓ CRN:[/green] [white]{MEROSHARE_CRN}[/white]")

    # Disclaimer check
    disclaimer_checkbox = wait.until(
        EC.presence_of_element_located((By.ID, "disclaimer"))
    )
    disclaimer_checkbox.click()
    console.print("[green]  ✓ Disclaimer accepted[/green]")

    # Submit the application
    footer_divs = wait.until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".card-footer"))
    )

    # Find the submit button - look for button with text "Submit" or in the second footer
    submit_btn = None
    for footer in footer_divs:
        try:
            buttons = footer.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                if (
                    "submit" in btn.text.lower()
                    or btn.get_attribute("type") == "submit"
                ):
                    submit_btn = btn
                    break
            if submit_btn:
                break
        except Exception:
            continue

    # Fallback to old method if smart search failed
    if not submit_btn and len(footer_divs) > 1:
        submit_btn = footer_divs[1].find_element(By.TAG_NAME, "button")

    if submit_btn:
        submit_btn.click()
        console.print("[green]  ✓ Form submitted[/green]")
        time.sleep(2)
    else:
        console.print("[red]  ❌ Could not find submit button![/red]")
        return False

    # PIN Fill
    pin_input = wait.until(EC.presence_of_element_located((By.ID, "transactionPIN")))
    pin_input.send_keys(MEROSHARE_PIN)
    console.print("[green]  ✓ Transaction PIN entered[/green]")

    # Final confirm button
    confirm_div = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".confirm-page-btn"))
    )
    confirm_btn = confirm_div.find_element(By.TAG_NAME, "button")
    confirm_btn.click()

    console.print()
    console.print(
        Panel(
            f"[bold green]✅ Application Ready![/bold green]\n\n"
            f"[white]Company:[/white] [bold cyan]{company_name}[/bold cyan]\n"
            f"[white]Shares:[/white] [bold cyan]{min_kitta}[/bold cyan]",
            border_style="yellow",
        )
    )
    console.print()

    return True


def get_input():
    def _raise(signum, frame):
        raise Exception("Input timeout")

    signal.signal(signal.SIGALRM, _raise)
    signal.alarm(4)  # Set timeout to 4 seconds
    try:
        return input().strip().lower()
    except Exception:
        return "n"
    finally:
        signal.alarm(0)  # Disable the alarm


# Main application loop
applied = 0
while True:
    companies = fetch_companies()
    if not companies and applied == 0:
        console.print()
        console.print("[bold red]❌ No companies found![/bold red]")
        console.print("[yellow]💡 There may be no IPOs available right now[/yellow]")
        console.print()
        exit(1)
    elif not companies and applied > 0:
        console.print()
        console.print(
            f"[bold green]✅ All done! Applied to {applied} company/companies[/bold green]"
        )
        console.print()
        break

    company = companies[0]
    if company and applied > 0:
        console.print()
        console.print(
            f"[bold cyan]📊 Progress: {applied} application(s) completed[/bold cyan]"
        )
        console.print()
        console.print(
            "  [yellow]Continue to the next company? (y/N):[/yellow] ",
            end="",
        )
        choice = get_input()
        if choice != "y":
            console.print()
            console.print("[yellow]👋 Stopping as requested[/yellow]")
            console.print()
            break

    success = apply_ipo(company)
    if not success:
        break

    applied += 1
    console.print(
        Panel(
            f"[bold green]✅ Application #{applied} Complete![/bold green]",
            style="bold green",
        )
    )
    navigate_to_asba()

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

driver.quit()
