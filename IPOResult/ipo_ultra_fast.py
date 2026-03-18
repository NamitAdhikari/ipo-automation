"""
IPO Result Checker - ULTRA FAST (API-Based)
Features:
- 73%+ captcha accuracy with custom CNN model
- Multi-BOID support from .env file
- Hybrid approach: Selenium once for cookies, then pure API calls
- Parallel execution with ThreadPoolExecutor (10-20x faster)
- Beautiful text table output
- Smart retry logic with captcha reload API
- Cookie refresh on expiry

Performance: 16 BOIDs in ~15-20 seconds (vs 12 minutes with pure Selenium)
"""

import argparse
import base64
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import requests

# Import our custom CNN captcha solver
from captcha_inference_advanced import CaptchaInferenceAdvanced
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions

# Initialize rich console
console = Console()


class UltraFastIPOChecker:
    """Ultra-fast IPO checker using API calls with parallel execution."""

    # API Endpoints
    BASE_URL = "https://iporesult.cdsc.com.np"
    INIT_API = "https://iporesult.cdsc.com.np/result/companyShares/fileUploaded"
    CHECK_API = "https://iporesult.cdsc.com.np/result/result/check"
    CAPTCHA_RELOAD_API = "https://iporesult.cdsc.com.np/result/captcha/reload/{}"

    # Configuration
    CONFIDENCE_THRESHOLD = 0.5
    MAX_CAPTCHA_RETRIES = 3
    MAX_API_RETRIES = 3

    def __init__(
        self,
        debug: bool = False,
        save_captchas: bool = True,
        save_failed_captchas: bool = True,
    ):
        self.debug = debug
        self.save_captchas = save_captchas
        self.save_failed_captchas = save_failed_captchas
        self.session = None  # requests.Session with cookies
        self.captcha_solver = None
        self.saved_captchas_count = 0
        self.saved_failed_captchas_count = 0
        self.selected_company = None

        # Create captcha dataset directories
        if self.save_captchas:
            os.makedirs("captcha_dataset_live", exist_ok=True)
        if self.save_failed_captchas:
            os.makedirs("captcha_dataset_failed", exist_ok=True)

        # Initialize CNN captcha solver
        try:
            self._log("Initializing CNN captcha solver...")
            self.captcha_solver = CaptchaInferenceAdvanced()
            self._log("✓ CNN captcha solver ready (73%+ accuracy)")
        except Exception as e:
            self._log(f"Failed to initialize CNN solver: {e}")
            raise RuntimeError("Cannot proceed without captcha solver")

    def _log(self, message: str):
        """Debug logging."""
        if self.debug:
            print(f"[DEBUG] {message}")

    def _save_captcha_image(
        self, captcha_text: str, captcha_image: np.ndarray
    ) -> bool:
        """Save successfully validated captcha to dataset."""
        if not self.save_captchas or captcha_image is None:
            return False

        try:
            dataset_dir = "captcha_dataset_live"
            timestamp = int(time.time() * 1000)
            filename = f"{captcha_text}_{timestamp}.png"
            filepath = os.path.join(dataset_dir, filename)

            cv2.imwrite(filepath, captcha_image)
            self.saved_captchas_count += 1
            self._log(f"💾 Saved captcha: {filename}")
            return True
        except Exception as e:
            self._log(f"⚠️ Failed to save captcha: {e}")
            return False

    def _save_failed_captcha_image(
        self, predicted_text: str, captcha_image: np.ndarray
    ) -> bool:
        """Save failed captcha image for manual labeling later."""
        if not self.save_failed_captchas or captcha_image is None:
            return False

        try:
            dataset_dir = "captcha_dataset_failed"
            timestamp = int(time.time() * 1000)
            filename = f"{predicted_text}_{timestamp}.png"
            filepath = os.path.join(dataset_dir, filename)

            cv2.imwrite(filepath, captcha_image)
            self.saved_failed_captchas_count += 1
            self._log(f"📝 Saved failed captcha for labeling: {filename}")
            return True
        except Exception as e:
            self._log(f"⚠️ Failed to save failed captcha: {e}")
            return False

    def acquire_cookies_with_browser(self) -> bool:
        """
        Open browser once to acquire session cookies.
        Returns True if successful, False if bot detection triggered.
        """
        console.print("\n[dim]Acquiring session cookies via browser...[/dim]")

        driver = None
        try:
            # Initialize Chrome with stealth options
            chrome_options = ChromeOptions()
            chrome_options.add_argument(
                "--disable-blink-features=AutomationControlled"
            )
            chrome_options.add_experimental_option(
                "excludeSwitches", ["enable-automation"]
            )
            chrome_options.add_experimental_option("useAutomationExtension", False)

            driver = webdriver.Chrome(options=chrome_options)
            driver.maximize_window()

            # Navigate to main page
            self._log(f"Navigating to {self.BASE_URL}")
            driver.get(self.BASE_URL)
            time.sleep(5)  # Let page fully load

            # Basic bot detection check
            page_source = driver.page_source.lower()
            page_title = driver.title.lower()

            # Check for bot detection indicators
            bot_indicators = [
                "request rejected",
                "tsbrpframe",
                "access denied",
                "forbidden",
            ]

            for indicator in bot_indicators:
                if indicator in page_source or indicator in page_title:
                    console.print(
                        f"[red]❌ Bot detection triggered: '{indicator}' found[/red]"
                    )
                    driver.quit()
                    return False

            # Extract cookies
            selenium_cookies = driver.get_cookies()
            self._log(f"Extracted {len(selenium_cookies)} cookies from browser")

            # Close browser
            driver.quit()

            # Create requests session and inject cookies
            self.session = requests.Session()
            for cookie in selenium_cookies:
                self.session.cookies.set(cookie["name"], cookie["value"])

            # Set required headers (from curl analysis)
            self.session.headers.update(
                {
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "en-US",
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
                    "Referer": "https://iporesult.cdsc.com.np/",
                }
            )

            console.print("[green]✓[/green] Session cookies acquired successfully")
            return True

        except Exception as e:
            self._log(f"Error acquiring cookies: {e}")
            console.print(f"[red]❌ Failed to acquire cookies: {e}[/red]")
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            return False

    def fetch_init_data(self) -> Optional[Dict]:
        """
        Call Init API to get captcha and company list.
        Returns: {companies: [...], captcha_base64: str, captcha_identifier: str}
        """
        try:
            self._log("Calling Init API...")
            resp = self.session.get(self.INIT_API, timeout=10)

            # Check for API rejection
            if self._detect_api_bot_rejection(resp):
                console.print("[yellow]⚠️ Init API rejected request[/yellow]")
                return None

            data = resp.json()
            body = data.get("body", {})

            captcha_data = body.get("captchaData", {})
            companies = body.get("companyShareList", [])

            self._log(f"Received {len(companies)} companies and captcha")

            return {
                "companies": companies[:5],  # Top 5 companies
                "captcha_base64": captcha_data.get("captcha"),
                "captcha_identifier": captcha_data.get("captchaIdentifier"),
            }

        except Exception as e:
            self._log(f"Error fetching init data: {e}")
            return None

    def _detect_api_bot_rejection(self, response) -> bool:
        """Check if API response indicates bot detection or rejection."""
        # Check status code
        if response.status_code in [403, 429, 503]:
            self._log(f"API returned rejection status code: {response.status_code}")
            return True

        # Check response body
        try:
            text = response.text.lower()
            rejection_keywords = [
                "rejected",
                "blocked",
                "forbidden",
                "challenge",
                "access denied",
            ]
            if any(kw in text for kw in rejection_keywords):
                self._log(f"API response contains rejection keyword")
                return True
        except:
            pass

        return False

    def solve_captcha_from_base64(
        self, base64_str: str
    ) -> Tuple[Optional[str], Optional[np.ndarray], float]:
        """
        Decode base64 captcha and solve with CNN.
        Returns: (captcha_text, captcha_image, confidence)
        """
        try:
            # Decode base64
            img_data = base64.b64decode(base64_str)
            nparr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img is None:
                self._log("Failed to decode captcha image")
                return None, None, 0.0

            # Check for blank captcha
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            if np.std(gray) < 10:
                self._log("Detected blank captcha")
                return None, None, 0.0

            # Solve with CNN
            prediction = self.captcha_solver.predict(
                img, strategy="best", num_attempts=7
            )

            result = prediction["result"]
            confidence = prediction["confidence"]

            self._log(f"CNN prediction: {result} (confidence: {confidence:.4f})")

            return result, img, confidence

        except Exception as e:
            self._log(f"Error solving captcha: {e}")
            return None, None, 0.0

    def reload_captcha(self, old_identifier: str) -> Optional[Dict]:
        """
        Call Captcha Reload API to get fresh captcha.
        Returns: {captcha_base64: str, captcha_identifier: str}
        """
        try:
            url = self.CAPTCHA_RELOAD_API.format(old_identifier)
            self._log(f"Calling Captcha Reload API: {url}")

            resp = self.session.post(url, timeout=10)

            if self._detect_api_bot_rejection(resp):
                self._log("Captcha Reload API rejected request")
                return None

            data = resp.json()
            body = data.get("body", {})

            if body:
                captcha_data = body.get("captchaData", {})
                return {
                    "captcha_base64": captcha_data.get("captcha"),
                    "captcha_identifier": captcha_data.get("captchaIdentifier"),
                }

            return None

        except Exception as e:
            self._log(f"Error reloading captcha: {e}")
            return None

    def check_single_boid(self, boid: str, company_id: int) -> Dict:
        """
        Check IPO result for a single BOID using API calls.
        This function is designed to run in parallel.

        Returns: result dict with status, quantity, message, error, boid
        """
        max_attempts = self.MAX_CAPTCHA_RETRIES

        # First, get initial captcha
        init_data = self.fetch_init_data()
        if not init_data:
            return {
                "status": "Error",
                "quantity": 0,
                "message": "Failed to fetch captcha",
                "error": "INIT_API_FAILED",
                "boid": boid,
            }

        captcha_id = init_data["captcha_identifier"]
        captcha_base64 = init_data["captcha_base64"]

        for attempt in range(1, max_attempts + 1):
            try:
                self._log(
                    f"BOID {boid} - Attempt {attempt}/{max_attempts} (captcha_id: {captcha_id[:8]}...)"
                )

                # Solve captcha
                captcha_text, captcha_img, confidence = self.solve_captcha_from_base64(
                    captcha_base64
                )

                if not captcha_text:
                    self._log(f"BOID {boid} - Failed to solve captcha")
                    # Try reloading captcha
                    if attempt < max_attempts:
                        reload_data = self.reload_captcha(captcha_id)
                        if reload_data:
                            captcha_id = reload_data["captcha_identifier"]
                            captcha_base64 = reload_data["captcha_base64"]
                            continue
                    return {
                        "status": "Error",
                        "quantity": 0,
                        "message": "Failed to solve captcha",
                        "error": "CAPTCHA_SOLVE_FAILED",
                        "boid": boid,
                    }

                if confidence < self.CONFIDENCE_THRESHOLD:
                    self._log(
                        f"BOID {boid} - Low confidence: {confidence:.4f}, but proceeding"
                    )

                # Submit check request
                payload = {
                    "companyShareId": company_id,
                    "boid": boid,
                    "userCaptcha": captcha_text,
                    "captchaIdentifier": captcha_id,
                }

                self._log(f"BOID {boid} - Submitting check with captcha: {captcha_text}")
                self._log(f"  → POST {self.CHECK_API}")
                self._log(f"  → Payload: {payload}")
                
                resp = self.session.post(self.CHECK_API, json=payload, timeout=15)
                
                self._log(f"  ← Status: {resp.status_code}")
                self._log(f"  ← Response: {resp.text[:500]}")

                # Check for API rejection
                if self._detect_api_bot_rejection(resp):
                    return {
                        "status": "Error",
                        "quantity": 0,
                        "message": "API rejected request (cookies may have expired)",
                        "error": "REJECTED",
                        "boid": boid,
                    }

                # Parse response
                result = self._parse_check_response(resp, captcha_text, captcha_img)
                result["boid"] = boid

                # If captcha was invalid, retry with new captcha
                if result.get("error") == "INVALID_CAPTCHA":
                    self._log(f"BOID {boid} - Invalid captcha, retrying...")
                    self._log(f"  ❌ SAVING FAILED CAPTCHA: {captcha_text}")

                    # Save failed captcha
                    if captcha_img is not None:
                        saved = self._save_failed_captcha_image(captcha_text, captcha_img)
                        self._log(f"  → Failed captcha saved: {saved}")
                        self._log(f"  → Failed captcha counter: {self.saved_failed_captchas_count}")

                    if attempt < max_attempts:
                        # Get new captcha via reload API
                        reload_data = self.reload_captcha(captcha_id)
                        if reload_data and reload_data.get("captcha_identifier") and reload_data.get("captcha_base64"):
                            captcha_id = reload_data["captcha_identifier"]
                            captcha_base64 = reload_data["captcha_base64"]
                            self._log(f"BOID {boid} - Got new captcha via reload API")
                            time.sleep(1)  # Brief delay before retry
                            continue
                        else:
                            # Reload failed, try full init
                            self._log(f"BOID {boid} - Reload API failed, fetching new captcha via Init API")
                            init_data = self.fetch_init_data()
                            if init_data and init_data.get("captcha_identifier") and init_data.get("captcha_base64"):
                                captcha_id = init_data["captcha_identifier"]
                                captcha_base64 = init_data["captcha_base64"]
                                self._log(f"BOID {boid} - Got new captcha via Init API")
                                continue
                            else:
                                self._log(f"BOID {boid} - Failed to get new captcha from both Reload and Init APIs")
                                # Continue to next attempt or fail

                    # Max attempts reached
                    return {
                        "status": "Error",
                        "quantity": 0,
                        "message": "Invalid captcha after max retries",
                        "error": "MAX_CAPTCHA_ATTEMPTS",
                        "boid": boid,
                    }

                # Success! Save captcha ONLY if it was validated by the API
                # captcha_valid=True means:
                # 1. success=True with allotment message, OR
                # 2. success=False with EXACT "Sorry, not alloted for the entered BOID." message
                if result.get("captcha_valid") is True:
                    self._log(f"✅ CAPTCHA VALIDATED BY API: {result.get('status')}")
                    self._log(f"  → SAVING SUCCESSFUL CAPTCHA: {captcha_text}")
                    if captcha_img is not None:
                        saved = self._save_captcha_image(captcha_text, captcha_img)
                        self._log(f"  → Successful captcha saved: {saved}")
                        self._log(f"  → Success captcha counter: {self.saved_captchas_count}")
                else:
                    self._log(f"⚠️  CAPTCHA NOT VALIDATED: {result.get('status')} (error: {result.get('error')})")
                    self._log(f"  → NOT saving to success dataset")

                return result

            except Exception as e:
                self._log(f"BOID {boid} - Exception in attempt {attempt}: {e}")
                if attempt == max_attempts:
                    return {
                        "status": "Error",
                        "quantity": 0,
                        "message": str(e),
                        "error": "EXCEPTION",
                        "boid": boid,
                    }
                time.sleep(1)

        # Should not reach here, but just in case
        return {
            "status": "Error",
            "quantity": 0,
            "message": "Max attempts reached",
            "error": "MAX_ATTEMPTS",
            "boid": boid,
        }

    def _parse_check_response(
        self, response, captcha_text: str, captcha_img: Optional[np.ndarray]
    ) -> Dict:
        """
        Parse the Check API response.

        Response format:
        Success: {"success": true, "message": "Congratulation Alloted !!! Alloted quantity : 10", "body": null}
        Failed: {"success": false, "message": "Sorry, not alloted for the entered BOID. ", "body": null}
        """
        try:
            # First, check response status
            self._log(f"Response status code: {response.status_code}")
            
            # Try to get JSON data
            try:
                data = response.json()
            except Exception as json_err:
                self._log(f"Failed to parse JSON response: {json_err}")
                self._log(f"Response text: {response.text[:200]}")
                return {
                    "status": "Error",
                    "quantity": 0,
                    "message": "Invalid JSON response from API",
                    "error": "JSON_PARSE_ERROR",
                    "captcha_valid": False,  # DO NOT save on parse errors
                }
            
            # Handle None response
            if data is None:
                self._log("Response data is None")
                return {
                    "status": "Error",
                    "quantity": 0,
                    "message": "Empty response from API",
                    "error": "EMPTY_RESPONSE",
                    "captcha_valid": False,  # DO NOT save on empty responses
                }

            # Extract fields
            success = data.get("success", False)
            message = data.get("message", "")
            body = data.get("body")
            message_lower = message.lower()

            # COMPREHENSIVE DEBUG LOG
            self._log("=" * 60)
            self._log(f"PARSING API RESPONSE:")
            self._log(f"  success: {success} (type: {type(success)})")
            self._log(f"  message: '{message}'")
            self._log(f"  body: {body}")
            self._log(f"  Full response: {data}")
            self._log("=" * 60)

            # Check for invalid captcha FIRST
            if "captcha" in message_lower and (
                "incorrect" in message_lower or "invalid" in message_lower or "wrong" in message_lower
            ):
                self._log("DECISION: Invalid captcha detected")
                return {
                    "status": "Error",
                    "quantity": 0,
                    "message": "Invalid captcha",
                    "error": "INVALID_CAPTCHA",
                    "captcha_valid": False,  # DO NOT save invalid captchas to success dataset
                }

            # CRITICAL: Check for exact "not allotted" message
            # Only save captcha if we get this EXACT message (meaning captcha was correct)
            if "sorry, not alloted for the entered boid" in message_lower:
                self._log("DECISION: Not Allotted (exact message match - CAPTCHA WAS CORRECT)")
                return {
                    "status": "Not Allotted",
                    "quantity": 0,
                    "message": "Not allotted",
                    "error": None,
                    "captcha_valid": True,  # Flag: captcha was correct, save it
                }

            # Check for explicit success=true AND allotment keywords
            if success is True:
                self._log("SUCCESS is TRUE, checking for allotment keywords...")
                
                if "congratulation" in message_lower or "alloted" in message_lower or "allotted" in message_lower:
                    self._log("DECISION: Allotted (success=True AND found allotment keywords - CAPTCHA WAS CORRECT)")
                    
                    # Try to extract quantity
                    quantity_match = re.search(r"quantity\s*:?\s*(\d+)", message_lower)
                    if quantity_match:
                        quantity = int(quantity_match.group(1))
                        self._log(f"  Extracted quantity: {quantity}")
                    else:
                        quantity = "?"
                        self._log("  Could not extract quantity from message")

                    return {
                        "status": "Allotted",
                        "quantity": quantity,
                        "message": f"Allotted {quantity} shares"
                        if quantity != "?"
                        else "Allotted",
                        "error": None,
                        "captcha_valid": True,  # Flag: captcha was correct, save it
                    }
                else:
                    self._log("SUCCESS is TRUE but no allotment keywords found - treating as unknown")

            # All other cases - DO NOT SAVE CAPTCHA
            # This includes: bot detection, cookie expiry, other errors
            self._log(f"DECISION: Other response (success={success}) - DO NOT SAVE CAPTCHA")
            return {
                "status": "Not Allotted" if success is False else "Unknown",
                "quantity": 0,
                "message": message or "Unknown response",
                "error": "UNKNOWN_RESPONSE",
                "captcha_valid": False,  # DO NOT save captcha for unknown responses
            }

        except Exception as e:
            self._log(f"EXCEPTION in _parse_check_response: {e}")
            import traceback
            self._log(traceback.format_exc())
            return {
                "status": "Error",
                "quantity": 0,
                "message": f"Failed to parse response: {e}",
                "error": "PARSE_ERROR",
                "captcha_valid": False,  # DO NOT save on exceptions
            }

    def check_multiple_boids_parallel(
        self, boids: List[str], company_id: int, max_workers: int = 10
    ) -> List[Dict]:
        """
        Check multiple BOIDs in parallel using ThreadPoolExecutor.
        Shows progress as each BOID completes.
        """
        results = []
        rejection_count = 0

        console.print(
            f"\n[bold cyan]{'─' * 70}[/bold cyan]"
        )
        console.print(
            f"[bold cyan]Checking {len(boids)} BOID(s) in parallel with {max_workers} workers[/bold cyan]"
        )
        console.print(f"[bold cyan]{'─' * 70}[/bold cyan]\n")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all BOID checks
            future_to_boid = {
                executor.submit(self.check_single_boid, boid, company_id): boid
                for boid in boids
            }

            # Collect results as they complete
            completed = 0
            for future in as_completed(future_to_boid):
                boid = future_to_boid[future]
                completed += 1

                try:
                    result = future.result()
                    results.append(result)

                    # Display progress (similar to current flow)
                    status = result.get("status", "Unknown")
                    quantity = result.get("quantity", 0)
                    boid_display = f"{boid[:6]}...{boid[-4:]}"

                    if status == "Allotted":
                        console.print(
                            f"[{completed}/{len(boids)}] [bold]BOID {boid_display}:[/bold] [green]✅ Allotted ({quantity} shares)[/green]"
                        )
                    elif status == "Not Allotted":
                        console.print(
                            f"[{completed}/{len(boids)}] [bold]BOID {boid_display}:[/bold] [red]❌ Not Allotted[/red]"
                        )
                    else:
                        error_msg = result.get("message", "Unknown error")
                        console.print(
                            f"[{completed}/{len(boids)}] [bold]BOID {boid_display}:[/bold] [yellow]⚠️ {status} - {error_msg}[/yellow]"
                        )

                    # Check for cookie expiry (multiple rejections)
                    if result.get("error") == "REJECTED":
                        rejection_count += 1
                        if rejection_count >= 3:
                            console.print(
                                "\n[yellow]⚠️ Multiple API rejections detected - cookies may have expired[/yellow]"
                            )
                            console.print(
                                "[dim]Suggestion: Restart the script to refresh cookies[/dim]\n"
                            )

                except Exception as e:
                    console.print(
                        f"[{completed}/{len(boids)}] [bold]BOID {boid[:6]}...{boid[-4:]}:[/bold] [red]❌ Error: {e}[/red]"
                    )
                    results.append(
                        {
                            "status": "Error",
                            "quantity": 0,
                            "message": str(e),
                            "error": "FUTURE_EXCEPTION",
                            "boid": boid,
                        }
                    )

        return results

    def display_results_table(self, ipo_name: str, results: List[Dict]):
        """Display results in a beautiful rich table (same as existing script)."""
        console.print()

        # Create rich table
        table = Table(
            title=f"[bold cyan]IPO RESULT SUMMARY[/bold cyan]\n[dim]{ipo_name}[/dim]",
            show_header=True,
            header_style="bold magenta",
            border_style="cyan",
        )

        table.add_column("BOID", style="dim", width=18)
        table.add_column("Status", justify="center", width=20)
        table.add_column("Quantity", justify="center", width=10)
        table.add_column("Message", width=30)

        # Data rows
        for result in results:
            boid = result.get("boid", "Unknown")
            status = result.get("status", "Unknown")
            quantity = result.get("quantity", 0)
            message = result.get("message", "")

            # Format status with colors
            if status == "Allotted":
                qty_str = str(quantity) if quantity != "?" else "?"
                status_display = f"[green]✅ {status}[/green]"
                qty_display = f"[green bold]{qty_str}[/green bold]"
                message_display = (
                    f"[green]{message[:28]}[/green]"
                    if len(message) > 28
                    else f"[green]{message}[/green]"
                )
            elif status == "Not Allotted":
                qty_str = "0"
                status_display = f"[red]❌ {status}[/red]"
                qty_display = f"[dim]{qty_str}[/dim]"
                message_display = (
                    f"[dim]{message[:28]}[/dim]"
                    if len(message) > 28
                    else f"[dim]{message}[/dim]"
                )
            else:
                qty_str = "-"
                status_display = f"[yellow]⚠️  {status}[/yellow]"
                qty_display = f"[yellow]{qty_str}[/yellow]"
                message_display = (
                    f"[yellow]{message[:28]}[/yellow]"
                    if len(message) > 28
                    else f"[yellow]{message}[/yellow]"
                )

            # Truncate BOID
            boid_display = f"{boid[:6]}...{boid[-4:]}"

            table.add_row(boid_display, status_display, qty_display, message_display)

        console.print(table)
        console.print()


def load_boids_from_env() -> List[str]:
    """Load BOID numbers from .env file."""
    load_dotenv()
    boid_str = os.getenv("BOID", "")

    if not boid_str:
        return []

    # Split by comma and clean up
    boids = [boid.strip() for boid in boid_str.split(",") if boid.strip()]
    return boids


def main():
    parser = argparse.ArgumentParser(
        description="Ultra-Fast IPO Result Checker - API-Based with Parallel Execution"
    )

    parser.add_argument("--boid", type=str, help="BOID number (overrides .env)")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument(
        "--auto", action="store_true", help="Auto-select first IPO (non-interactive)"
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=10,
        help="Number of parallel workers (default: 10)",
    )
    parser.add_argument(
        "--no-save-captcha",
        action="store_true",
        help="Disable automatic captcha dataset collection",
    )
    parser.add_argument(
        "--no-save-failed-captchas",
        action="store_true",
        help="Disable saving failed captchas for manual labeling",
    )

    args = parser.parse_args()

    # Banner
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]IPO RESULT CHECKER - ULTRA FAST[/bold cyan]\n"
            "[dim]API-Based with Parallel Execution[/dim]\n"
            "[yellow]⚡ Powered by Custom CNN Model (73%+ Accuracy)[/yellow]\n"
            "[green]🚀 10-20x faster than browser automation[/green]",
            border_style="cyan",
        )
    )
    console.print()

    # Load BOIDs
    if args.boid:
        boids = [args.boid]
        console.print(
            f"[green]✓[/green] Using BOID from command line: [cyan]{args.boid}[/cyan]"
        )
    else:
        boids = load_boids_from_env()
        if not boids:
            console.print("[red]❌ No BOID provided![/red]")
            console.print("\n[yellow]Please either:[/yellow]")
            console.print("  [dim]1. Add BOID to .env file (see .env.sample)[/dim]")
            console.print(
                "  [dim]2. Use --boid flag: python ipo_ultra_fast.py --boid 1301260001246310[/dim]"
            )
            return 1
        console.print(
            f"[green]✓[/green] Loaded [cyan]{len(boids)}[/cyan] BOID(s) from .env file"
        )

    # Initialize checker
    checker = UltraFastIPOChecker(
        debug=args.debug,
        save_captchas=not args.no_save_captcha,
        save_failed_captchas=not args.no_save_failed_captchas,
    )

    try:
        # Phase 1: Acquire cookies via browser (one-time)
        start_time = time.time()

        if not checker.acquire_cookies_with_browser():
            console.print("\n[red]❌ Failed to acquire session cookies[/red]")
            console.print("[yellow]⚠️  Troubleshooting:[/yellow]")
            console.print("   [dim]1. Wait 15-30 minutes before trying again[/dim]")
            console.print("   [dim]2. Check your internet connection[/dim]")
            console.print(
                "   [dim]3. The website may be blocking automated access[/dim]"
            )
            return 1

        # Phase 2: Fetch companies and select IPO
        console.print("\n[dim]Fetching available IPOs...[/dim]")
        init_data = checker.fetch_init_data()

        if not init_data or not init_data.get("companies"):
            console.print("[red]❌ Could not fetch IPO list[/red]")
            return 1

        companies = init_data["companies"]

        # Display and select company
        console.print()
        if len(companies) == 1:
            console.print(
                Panel(
                    f"[cyan]{companies[0].get('name', 'Unknown')}[/cyan]",
                    title="[bold]Using IPO[/bold]",
                    border_style="blue",
                )
            )
            selected_company = companies[0]
        else:
            # Show top 5 companies (or all if less than 5)
            display_count = min(5, len(companies))
            
            console.print(
                Panel.fit("[bold cyan]Available IPOs[/bold cyan]", border_style="cyan")
            )
            for idx in range(display_count):
                name = companies[idx].get("name", "Unknown")
                console.print(f"  [yellow]{idx + 1}.[/yellow] {name}")
            
            # Show message if there are more companies
            if len(companies) > 5:
                console.print(f"  [dim]... and {len(companies) - 5} more (showing top 5)[/dim]")
            
            console.print()

            # Get user choice or auto-select
            if args.auto:
                choice_idx = 0
                console.print(
                    f"[green]✓[/green] Auto-selected: [cyan]{companies[0].get('name', 'Unknown')}[/cyan]"
                )
            else:
                # Interactive selection (limit to top 5)
                max_choice = display_count
                while True:
                    try:
                        choice = console.input(
                            f"[bold]Select IPO (1-{max_choice}):[/bold] "
                        ).strip()
                        choice_idx = int(choice) - 1

                        if 0 <= choice_idx < max_choice:
                            break
                        else:
                            console.print(
                                f"[yellow]Please enter a number between 1 and {max_choice}[/yellow]"
                            )
                    except (ValueError, KeyboardInterrupt, EOFError):
                        console.print("\n[yellow]Operation cancelled by user[/yellow]")
                        return 0

            selected_company = companies[choice_idx]

        company_id = selected_company.get("id")
        company_name = selected_company.get("name", "Unknown IPO")

        console.print(
            f"\n[green]✓[/green] Selected: [cyan]{company_name}[/cyan] (ID: {company_id})"
        )

        # Phase 3: Check BOIDs in parallel
        results = checker.check_multiple_boids_parallel(
            boids, company_id, max_workers=args.parallel
        )

        # Phase 4: Display results
        checker.display_results_table(company_name, results)

        # Show statistics
        elapsed_time = time.time() - start_time
        total = len(results)
        allotted = sum(1 for r in results if r.get("status") == "Allotted")
        not_allotted = sum(1 for r in results if r.get("status") == "Not Allotted")
        errors = sum(1 for r in results if r.get("status") == "Error")

        console.print(f"[bold]Statistics:[/bold]")
        console.print(f"  Total BOIDs: {total}")
        console.print(f"  [green]✅ Allotted: {allotted}[/green]")
        console.print(f"  [red]❌ Not Allotted: {not_allotted}[/red]")
        console.print(f"  [yellow]⚠️  Errors: {errors}[/yellow]")
        console.print(f"\n[bold]Performance:[/bold]")
        console.print(f"  ⏱️  Total time: {elapsed_time:.1f} seconds")
        console.print(f"  🚀 Average: {elapsed_time/total:.1f}s per BOID")

        if checker.saved_captchas_count > 0:
            console.print(
                f"\n[dim]💾 Saved {checker.saved_captchas_count} captcha(s) to dataset[/dim]"
            )
        if checker.saved_failed_captchas_count > 0:
            console.print(
                f"[dim]📝 Saved {checker.saved_failed_captchas_count} failed captcha(s) for labeling[/dim]"
            )

        console.print()
        return 0

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Operation cancelled by user[/yellow]")
        return 0
    except Exception as e:
        console.print(f"\n[red]❌ Unexpected error: {e}[/red]")
        if args.debug:
            import traceback

            console.print(traceback.format_exc())
        return 1


if __name__ == "__main__":
    exit(main())
