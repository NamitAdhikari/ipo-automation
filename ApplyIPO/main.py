import atexit
import os
import time
from typing import TYPE_CHECKING

from dotenv import load_dotenv
from rich.console import Console
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
    console.print(
        (
            "[red]Error: MEROSHARE_USERNAME, MEROSHARE_PASSWORD, MEROSHARE_DP, MEROSHARE_CRN, and MEROSHARE_PIN environment variables "
            "must be set in the .env file."
        )
    )
    exit(1)

chrome_options = ChromeOptions()
driver: "WebDriverChrome" = Chrome(options=chrome_options)  # type: ignore
driver.maximize_window()

atexit.register(lambda: driver.quit())

wait = WebDriverWait(driver, 5)

# open meroshare page
driver.get("https://meroshare.cdsc.com.np")

# ====================================
#               LOGIN FLOW
# ===================================

# DP Selector
selector = wait.until(EC.presence_of_element_located((By.ID, "selectBranch")))
selector.click()


# Find all available options in the dropdown
# options = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".option")))
# print("Available options: ", options)

selectable = wait.until(
    EC.presence_of_element_located((By.CSS_SELECTOR, ".select2-hidden-accessible"))
)
options = selectable.find_elements(By.CSS_SELECTOR, "option")


normalized_dp = MEROSHARE_DP.strip().lower()
eligible_dp = None
eligible_dp_count = 0
for option in options:
    if eligible_dp_count > 1:
        break

    if option.text.strip().lower().__contains__(normalized_dp):
        eligible_dp_count += 1
        eligible_dp = option

if not eligible_dp:
    console.print(
        f"[red]Error: No eligible DP found for '{MEROSHARE_DP}'. Please check the .env file and try again."
    )
    exit(1)


if eligible_dp_count > 1:
    console.print(
        f"[yellow]Warning: Multiple DPs found matching '{MEROSHARE_DP}'. Please select the correct one from the list."
    )
    searchable = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".select2-search__field"))
    )
    searchable.send_keys(MEROSHARE_DP)

    search_results = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".select2-results__options"))
    )
    # li elements
    eligible_options = search_results.find_elements(
        By.CSS_SELECTOR, ".select2-results__option"
    )

    eligible_dps = {}
    console.print("[green]Eligible DPs:[/green]")

    for idx, li_elem in enumerate(eligible_options, start=1):
        eligible_dps[idx] = li_elem
        console.print(f"[cyan]{idx}.[/cyan] {li_elem.text.strip()}")

    if not eligible_dps:
        console.print(
            f"[red]Error: No eligible DP found for '{MEROSHARE_DP}'. Please check the .env file and try again."
        )
        exit(1)

    while True:
        try:
            choice = int(input("Enter the number corresponding to your DP choice: "))
            if 1 <= choice <= len(eligible_dps):
                selectable_dp = list(eligible_dps.values())[choice - 1]
                console.print(f"[green]Selected DP: {selectable_dp.text}")
                selectable_dp.click()
                break
            else:
                console.print("[red]Invalid choice. Please enter a valid number.")
        except ValueError:
            console.print("[red]Invalid input. Please enter a number.")
else:
    eligible_dp.click()


# Click somewhere else to close the dropdown
wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".copyright"))).click()

username_input = wait.until(EC.presence_of_element_located((By.ID, "username")))
username_input.send_keys(MEROSHARE_USERNAME)

password_input = wait.until(EC.presence_of_element_located((By.ID, "password")))
password_input.send_keys(MEROSHARE_PASSWORD)

login_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".sign-in")))
login_button.click()


# try:
#     err_msg = wait.until(
#         EC.presence_of_element_located((By.CSS_SELECTOR, ".toast-message"))
#     )
#     console.print(f"[red]Login failed! {err_msg.text}[/red]")
#     exit(1)
# except TimeoutException:
#     console.print("[green]Login successful![/green]")
try:
    wait.until(EC.url_contains("/dashboard"))
    console.print("[green]Login successful![/green]")
except TimeoutException:
    console.print(
        "[red]Login failed! Please check your credentials and try again.[/red]"
    )
    exit(1)


# ====================================
#              Apply FLOW
# ==================================

console.print("[yellow]Navigating to ASBA application page...[/yellow]")


def navigate_to_asba():
    asba_menu = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".msi-asba")))
    asba_menu.click()


navigate_to_asba()


# Find all applications
def fetch_companies():
    companies = wait.until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".company-list"))
    )
    return companies


def apply_ipo(company: "WebElement"):
    company_detail = company.find_element(By.CSS_SELECTOR, ".company-name")
    spans = company_detail.find_elements(By.TAG_NAME, "span")

    company_name, *_, share_type, share_group = [span.text.strip() for span in spans]
    console.print(
        f"[green]Found Company: {company_name}, Share Type: {share_type}, Share Group: {share_group}[/green]"
    )

    apply_btn = company.find_element(By.CSS_SELECTOR, ".btn-issue")
    apply_btn.click()

    # Scroll down to the bottom of the page to load all elements
    container = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".card-body"))
    )
    driver.execute_script("window.scrollTo(0, arguments[0].scrollHeight);", container)

    # Find minimum kitta
    min_kitta_main_div = wait.until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".section-block"))
    )[1]

    # ipdb.set_trace()
    min_kitta_div = min_kitta_main_div.find_elements(By.CSS_SELECTOR, ".col-md-4")[5]
    min_kitta_form_div = min_kitta_div.find_element(By.CSS_SELECTOR, ".form-value")
    min_kitta = min_kitta_form_div.find_element(By.TAG_NAME, "span").text.strip()

    # Fill in the application form
    # Bank Select
    banks_select = wait.until(EC.presence_of_element_located((By.ID, "selectBank")))
    bank_options = banks_select.find_elements(By.TAG_NAME, "option")
    # The first option is usually a placeholder like "Please choose one"
    if len(bank_options) == 2:
        bank_options[1].click()
    else:
        raise ValueError(
            "Multiple bank options found! The script currently does not support multiple bank options."
        )

    # Account Number Fill
    account_number_select = wait.until(
        EC.presence_of_element_located((By.ID, "accountNumber"))
    )
    # API Call happens here, so introduce a wait to ensure options are loaded
    time.sleep(2)
    account_number_options = account_number_select.find_elements(By.TAG_NAME, "option")
    # The first option is usually a placeholder like "Please choose one"
    if len(account_number_options) == 2:
        account_number_options[1].click()
    else:
        raise ValueError(
            "Multiple account number options found! The script currently does not support multiple account number options."
        )

    # Kitta Fill
    kitta_input = wait.until(EC.presence_of_element_located((By.ID, "appliedKitta")))
    kitta_input.send_keys(min_kitta)

    # CRN Fill
    crn_input = wait.until(EC.presence_of_element_located((By.ID, "crnNumber")))
    crn_input.send_keys(MEROSHARE_CRN)

    # Disclaimer check
    disclaimer_checkbox = wait.until(
        EC.presence_of_element_located((By.ID, "disclaimer"))
    )
    disclaimer_checkbox.click()

    # Submit the application
    footer_div = wait.until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".card-footer"))
    )[1]
    submit_btn = footer_div.find_element(By.TAG_NAME, "button")
    submit_btn.click()

    # PIN Fill
    pin_input = wait.until(EC.presence_of_element_located((By.ID, "transactionPIN")))
    pin_input.send_keys(MEROSHARE_PIN)

    confirm_div = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".confirm-page-btn"))
    )
    confirm_btn = confirm_div.find_element(By.TAG_NAME, "button")
    # confirm_btn.click()
    console.print(f"[green]Application submitted for company: {company_name}[/green]")


applied = 0
while True:
    companies = fetch_companies()
    if not companies and applied == 0:
        console.print("[red]No companies found![/red]")
        exit(1)
    elif not companies and applied > 0:
        console.print(
            f"[yellow]No more companies found! You have applied to {applied} companies.[/yellow]"
        )
        break

    company = companies[0]
    if company and applied > 0:
        choice = (
            input(
                f"[yellow]Apply to the next company? (y/n) (Applied to {applied} companies so far)[/yellow] "
            )
            .strip()
            .lower()
        )
        if choice != "y":
            break

    apply_ipo(company)
    applied += 1

    # navigate_to_asba()


# Placeholder until script completes, to give me time to inspect page and debug if necessary
driver.quit()
