"""
IPO Result Checker - ENHANCED & FULLY AUTOMATED
Features:
- 73%+ captcha accuracy with custom CNN model
- Multi-BOID support from .env file
- Interactive IPO selection from latest 5 IPOs
- Beautiful text table output
- Request rejection retry with browser restart
- Graceful allotment status handling
- Headless mode support
"""

import argparse
import io
import os
import re
import time
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dotenv import load_dotenv

import cv2
import numpy as np
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from texttable import Texttable

# Import our custom CNN captcha solver
from captcha_inference_advanced import CaptchaInferenceAdvanced


class EnhancedIPOChecker:
    """Enhanced IPO checker with multi-BOID support and beautiful output."""
    
    BASE_URL = "https://iporesult.cdsc.com.np"
    CONFIDENCE_THRESHOLD = 0.5
    MAX_CAPTCHA_RETRIES = 3  # Retry captcha solve 3 times
    MAX_REJECTION_RETRIES = 3  # Restart browser 3 times on rejection
    
    def __init__(self, debug: bool = False, headless: bool = False):
        self.debug = debug
        self.headless = headless
        self.driver = None
        self.captcha_solver = None
        self.rejection_count = 0
        
        # Initialize CNN captcha solver
        try:
            self._log("Initializing CNN captcha solver...")
            self.captcha_solver = CaptchaInferenceAdvanced()
            self._log("✓ CNN captcha solver ready (73%+ accuracy)")
        except Exception as e:
            self._log(f"Failed to initialize CNN solver: {e}")
            raise RuntimeError("Cannot proceed without captcha solver")
        
    def _log(self, message: str):
        if self.debug:
            print(f"[DEBUG] {message}")
    
    def _init_driver(self):
        """Initialize or reinitialize the browser driver."""
        if self.driver is not None:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
        
        print("Initializing browser..." if not self.driver else "Restarting browser...")
        chrome_options = ChromeOptions()
        
        # CRITICAL: Match ipo_fully_auto.py exactly (minimal stealth that works)
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Only add headless if requested
        if self.headless:
            chrome_options.add_argument('--headless=new')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.maximize_window()
        
        print("✓ Browser ready")
    
    def close(self):
        """Close the browser."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
    
    def diagnose_bot_detection(self) -> dict:
        """
        Diagnostic tool to check if bot detection is triggered.
        Call this manually when troubleshooting, not during normal flow.
        
        Returns dict with: detected (bool), reason (str), screenshot_path (str or None)
        """
        try:
            page_source = self.driver.page_source.lower()
            title = self.driver.title.lower()
            
            result = {
                'detected': False,
                'reason': None,
                'screenshot_path': None
            }
            
            # Check for bot detection indicators
            bot_indicators = [
                'request rejected',
                'tsbrpframe',
                'access denied',
                'suspicious activity',
                'cloudflare',
                'just a moment',
            ]
            
            for indicator in bot_indicators:
                if indicator in page_source or indicator in title:
                    result['detected'] = True
                    result['reason'] = f"Found '{indicator}' in page"
                    
                    # Save screenshot
                    try:
                        timestamp = int(time.time() * 1000)
                        screenshot_path = f"/tmp/bot_detection_{timestamp}.png"
                        self.driver.save_screenshot(screenshot_path)
                        result['screenshot_path'] = screenshot_path
                    except:
                        pass
                    
                    return result
            
            # Check for missing elements
            has_form = '<form' in page_source
            has_captcha = 'img[alt="captcha"]' in page_source or 'img[alt="Captcha"]' in page_source
            has_ng_select = 'ng-select' in page_source
            
            if not has_form or (not has_captcha and not has_ng_select):
                result['detected'] = True
                result['reason'] = f"Missing elements: form={has_form}, captcha={has_captcha}, ng-select={has_ng_select}"
                
                try:
                    timestamp = int(time.time() * 1000)
                    screenshot_path = f"/tmp/bot_detection_missing_{timestamp}.png"
                    self.driver.save_screenshot(screenshot_path)
                    result['screenshot_path'] = screenshot_path
                except:
                    pass
            
            return result
            
        except Exception as e:
            return {
                'detected': False,
                'reason': f'Error during check: {e}',
                'screenshot_path': None
            }
    
    def get_available_ipos(self) -> List[Dict]:
        """Fetch available IPOs from the dropdown - MINIMAL VERSION to avoid bot detection."""
        try:
            self._log("Fetching available IPOs...")
            
            # Wait for ng-select to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "ng-select"))
            )
            
            time.sleep(2)
            
            # Get the default selection first
            default_text = self.driver.execute_script("""
                const ngSelect = document.querySelector('ng-select');
                if (!ngSelect) return '';
                const selected = ngSelect.querySelector('.ng-value-label');
                return selected ? selected.textContent.trim() : '';
            """)
            
            self._log(f"Default selection: {default_text}")
            
            # Try to open dropdown by clicking ng-select element directly
            try:
                ng_select = self.driver.find_element(By.TAG_NAME, "ng-select")
                ng_select.click()
                self._log("Clicked ng-select element")
            except Exception as e:
                self._log(f"Failed to click ng-select: {e}")
                # Fallback: try clicking arrow with JavaScript
                self.driver.execute_script("""
                    const ngSelect = document.querySelector('ng-select');
                    if (ngSelect) {
                        const arrow = ngSelect.querySelector('.ng-arrow-wrapper');
                        if (arrow) arrow.click();
                    }
                """)
            
            # Wait for dropdown to open and render
            time.sleep(2.5)
            
            # Get all IPO options with their ACTUAL DOM indices
            ipos = self.driver.execute_script("""
                const defaultText = arguments[0];
                const options = Array.from(document.querySelectorAll('.ng-dropdown-panel .ng-option'));
                
                // Build array with ACTUAL indices from DOM
                const validOptions = [];
                options.forEach((opt, actualIndex) => {
                    // Skip disabled options
                    if (opt.classList.contains('ng-option-disabled')) return;
                    // Skip marked/selected options that are placeholders
                    if (opt.classList.contains('ng-option-marked') && !opt.textContent.trim()) return;
                    // Skip empty options
                    const text = opt.textContent.trim();
                    if (!text || text.length < 5) return;
                    
                    validOptions.push({
                        index: actualIndex,  // ← Store ACTUAL DOM index, not filtered index
                        text: text,
                        isDefault: text === defaultText
                    });
                });
                
                return validOptions;
            """, default_text)
            
            # Close dropdown - CRITICAL: Must close properly or captcha will be blocked!
            # Use a gentle close that doesn't destroy DOM elements (for later reuse)
            self.driver.execute_script("""
                // First, try clicking away to close naturally
                document.body.click();
                
                // If panel is still visible, hide it with CSS instead of removing
                setTimeout(() => {
                    const panel = document.querySelector('.ng-dropdown-panel');
                    if (panel) {
                        panel.style.display = 'none';
                        panel.style.visibility = 'hidden';
                    }
                }, 100);
            """)
            time.sleep(1)  # Give it time to fully close
            
            self._log(f"Found {len(ipos) if ipos else 0} IPO(s)")
            
            if ipos and len(ipos) > 0:
                for i, ipo in enumerate(ipos):
                    default_marker = " [DEFAULT]" if ipo.get('isDefault') else ""
                    self._log(f"  {i+1}. {ipo['text'][:60]}{'...' if len(ipo['text']) > 60 else ''}{default_marker}")
                return ipos[:5]  # Return max 5
            else:
                # Fallback: just use default
                self._log("No IPOs found in dropdown, using default...")
                if default_text:
                    default_ipo = {
                        'index': 0,
                        'text': default_text,
                        'isDefault': True
                    }
                    self._log(f"Using default: {default_ipo['text']}")
                    return [default_ipo]
                
                return []
            
        except Exception as e:
            self._log(f"Error fetching IPOs: {e}")
            import traceback
            self._log(traceback.format_exc())
            return []
    
    def select_ipo(self, index: int) -> bool:
        """Select an IPO by index."""
        try:
            self._log(f"Selecting IPO at DOM index {index}...")
            print(f"    Opening dropdown...")
            
            # First, unhide any hidden dropdown panels from previous close
            self.driver.execute_script("""
                const panel = document.querySelector('.ng-dropdown-panel');
                if (panel) {
                    panel.style.display = '';
                    panel.style.visibility = '';
                }
            """)
            
            # Open dropdown
            self.driver.execute_script("""
                const index = arguments[0];
                const ngSelect = document.querySelector('ng-select');
                if (!ngSelect) {
                    console.log('ERROR: ng-select not found');
                    return false;
                }
                
                // Click to open dropdown
                ngSelect.click();
                console.log('Clicked ng-select to open dropdown');
            """, index)
            
            # Wait for dropdown to open and render
            time.sleep(2)
            print(f"    Clicking option at DOM index {index}...")
            
            # Click the option
            clicked = self.driver.execute_script("""
                const index = arguments[0];
                const options = document.querySelectorAll('.ng-dropdown-panel .ng-option');
                console.log('Total options in dropdown:', options.length);
                console.log('Attempting to click index:', index);
                
                if (options[index]) {
                    const optionText = options[index].textContent.trim();
                    console.log('Clicking option:', optionText);
                    options[index].click();
                    return true;
                }
                console.log('ERROR: Option not found at index:', index);
                return false;
            """, index)
            
            if not clicked:
                self._log(f"⚠️  Option at index {index} not found!")
                print(f"    ⚠️  Browser console shows option not found")
                return False
            
            # Wait for selection to register
            time.sleep(1)
            print(f"    Closing dropdown...")
            
            # Close the dropdown panel by hiding it (not removing)
            self.driver.execute_script("""
                document.body.click();
                setTimeout(() => {
                    const panel = document.querySelector('.ng-dropdown-panel');
                    if (panel) {
                        panel.style.display = 'none';
                        panel.style.visibility = 'hidden';
                    }
                }, 100);
            """)
            
            # Give it time to fully close
            time.sleep(1.5)
            
            self._log("✓ IPO selected and dropdown closed")
            return True
            
        except Exception as e:
            self._log(f"Error selecting IPO: {e}")
            import traceback
            self._log(traceback.format_exc())
            return False
    
    def solve_captcha_cnn(self) -> Optional[Dict]:
        """Solve captcha using CNN model."""
        try:
            # Check for rejection FIRST
            if self.check_for_rejection():
                print("\n⛔ REQUEST REJECTED BY MEROSHARE!")
                print("The website has blocked automated requests.")
                print("Browser will be restarted automatically...")
                return None
            
            # Get captcha image
            captcha_img = self.driver.find_element(By.CSS_SELECTOR, "img[alt='captcha']")
            
            # Wait for captcha to load (avoid blankCaptcha.png)
            time.sleep(0.5)
            
            # Screenshot captcha
            captcha_png = captcha_img.screenshot_as_png
            
            # Convert to numpy array
            nparr = np.frombuffer(captcha_png, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Check for blank captcha
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            if np.std(gray) < 10:  # Very low variance = blank
                self._log("Detected blank captcha")
                return None
            
            # Use CNN inference
            prediction = self.captcha_solver.predict(
                img, 
                strategy='best',
                num_attempts=7
            )
            
            result = prediction['result']
            confidence = prediction['confidence']
            
            self._log(f"CNN prediction: {result} (confidence: {confidence:.4f})")
            
            return {
                'result': result,
                'confidence': confidence
            }
            
        except Exception as e:
            self._log(f"Error in CNN solve: {e}")
            # Check if error was due to rejection
            if self.check_for_rejection():
                print("\n⛔ REQUEST REJECTED BY MEROSHARE!")
                print("The website has blocked automated requests.")
            return None
    
    def refresh_captcha(self) -> bool:
        """Refresh captcha by clicking refresh button."""
        try:
            refresh_xpath = "/html/body/app-root/app-allotment-result/div/div/div/div/form/div[2]/div[2]/div/div[2]/button[2]"
            button = self.driver.find_element(By.XPATH, refresh_xpath)
            button.click()
            time.sleep(1.5)
            self._log("Captcha refreshed")
            return True
        except Exception as e:
            self._log(f"Error refreshing captcha: {e}")
            return False
    
    def check_for_rejection(self) -> bool:
        """Check if request was rejected by MeroShare or bot challenge appeared."""
        try:
            # Check for bot challenge iframe
            bot_challenge = self.driver.execute_script("""
                const iframe = document.querySelector('iframe[id*="TSBrPFrame"]');
                return iframe !== null;
            """)
            
            if bot_challenge:
                self._log(f"⚠️  Bot challenge iframe detected!")
                return True
            
            page_text = self.driver.page_source.lower()
            page_title = self.driver.title.lower()
            
            # Check for rejection keywords
            rejection_keywords = [
                'rejected', 
                'blocked', 
                'consult with your administrator',
                'request rejected',
                'access denied',
                'forbidden',
                'challenge',
                'verify you are human'
            ]
            
            if any(keyword in page_text for keyword in rejection_keywords):
                self._log(f"⚠️  Rejection detected in page content")
                return True
            
            if any(keyword in page_title for keyword in rejection_keywords):
                self._log(f"⚠️  Rejection detected in page title: {page_title}")
                return True
            
            # Check current URL
            current_url = self.driver.current_url
            if 'error' in current_url.lower() or 'reject' in current_url.lower():
                self._log(f"⚠️  Rejection detected in URL: {current_url}")
                return True
                
            return False
        except Exception as e:
            self._log(f"Error checking rejection: {e}")
            return False
    
    def solve_captcha_with_retry(self, max_retries: int = None) -> Optional[str]:
        """Solve captcha with retry logic."""
        if max_retries is None:
            max_retries = self.MAX_CAPTCHA_RETRIES
        
        for retry in range(max_retries):
            # Check for rejection before attempting
            if self.check_for_rejection():
                self._log("⚠️  Request rejected detected during captcha solve")
                return None
            
            self._log(f"Attempting to solve captcha (attempt {retry + 1}/{max_retries})...")
            prediction = self.solve_captcha_cnn()
            
            if prediction is None:
                self._log(f"Failed to solve captcha (attempt {retry + 1}/{max_retries})")
                
                # Check if failure was due to rejection
                if self.check_for_rejection():
                    self._log("⚠️  Captcha solve failed due to request rejection")
                    return None
                
                if retry < max_retries - 1:
                    self._log("Refreshing captcha and retrying...")
                    if self.refresh_captcha():
                        time.sleep(1)
                        continue
                return None
            
            result = prediction['result']
            confidence = prediction['confidence']
            
            if confidence >= self.CONFIDENCE_THRESHOLD:
                self._log(f"✓ High confidence: {result} ({confidence:.4f})")
                return result
            else:
                self._log(f"⚠ Low confidence: {result} ({confidence:.4f})")
                if retry < max_retries - 1:
                    self._log("Refreshing captcha and retrying...")
                    if self.refresh_captcha():
                        time.sleep(1)
                        continue
                # Use low confidence prediction on last attempt
                self._log("Using low confidence prediction on last attempt")
                return result
        
        return None
    
    def submit_captcha(self, boid: str, captcha_text: str) -> Tuple[bool, str]:
        """
        Submit form with BOID and captcha.
        
        Returns:
            (success, status) where status is:
            - "success": Captcha accepted, got result page
            - "invalid_captcha": Captcha was wrong
            - "rejected": Request rejected by server
            - "error": Other error
        """
        try:
            # Check for rejection before submitting
            if self.check_for_rejection():
                self._log("⚠️  Rejection detected BEFORE submit")
                return False, "rejected"
            
            # Enter BOID
            boid_input = self.driver.find_element(By.ID, "boid")
            boid_input.clear()
            time.sleep(0.1)
            boid_input.send_keys(boid)
            time.sleep(0.2)
            
            # Enter captcha
            captcha_input = self.driver.find_element(By.ID, "userCaptcha")
            captcha_input.clear()
            time.sleep(0.1)
            
            # Type with slight delay (human-like)
            for char in captcha_text:
                captcha_input.send_keys(char)
                time.sleep(0.05)
            
            time.sleep(0.5)
            
            # Submit
            submit_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            try:
                submit_btn.click()
            except:
                self.driver.execute_script("arguments[0].click();", submit_btn)
            
            # Wait for response
            time.sleep(4)  # Longer wait to ensure page loads
            
            # CRITICAL: Check for rejection FIRST (highest priority)
            if self.check_for_rejection():
                self._log("⚠️  Rejection detected AFTER submit - request was blocked!")
                print(f"⚠️  Captcha '{captcha_text}' submitted but REQUEST WAS REJECTED by server")
                return False, "rejected"
            
            page_text = self.driver.page_source.lower()
            
            # Check for success FIRST (result page indicators)
            # MeroShare uses both "allotted" and "alloted" (typo)
            success_indicators = ['allotted', 'alloted', 'congratulation', 'sorry', 'applicant details']
            if any(indicator in page_text for indicator in success_indicators):
                self._log(f"✓ Captcha '{captcha_text}' accepted! Got result page")
                return True, "success"
            
            # Check for explicit captcha error messages (only check if no success indicators)
            captcha_error_indicators = [
                'captcha is incorrect',
                'invalid captcha',
                'wrong captcha',
                'captcha mismatch',
                'captcha does not match'
            ]
            if any(error in page_text for error in captcha_error_indicators):
                self._log(f"✗ Captcha '{captcha_text}' was incorrect")
                return False, "invalid_captcha"
            
            # Unknown response - log page content for debugging
            self._log(f"Unclear response for '{captcha_text}'")
            self._log(f"Page text snippet: {page_text[:300]}")
            
            # Default to error state rather than success
            return False, "error"
            
        except Exception as e:
            self._log(f"Error in submit: {e}")
            import traceback
            self._log(traceback.format_exc())
            return False, "error"
    
    def parse_result(self) -> Dict:
        """Parse the result page."""
        try:
            time.sleep(2)
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            body_lower = body_text.lower()
            
            self._log(f"Parsing result page text (first 300 chars):")
            self._log(f"  {body_text[:300]}")
            
            result = {
                'raw_text': body_text
            }
            
            # Check for "not allotted" or "not alloted" (MeroShare has typos!)
            if 'not allotted' in body_lower or 'not alloted' in body_lower or ('sorry' in body_lower and 'allot' in body_lower):
                result['status'] = 'Not Allotted'
                result['quantity'] = 0
                result['message'] = 'Not allotted'
                self._log("Result: Not Allotted")
            # Check for successful allotment - MeroShare uses "Congratulation Alloted" (with typos!)
            elif 'congratulation' in body_lower or ('alloted' in body_lower and 'not alloted' not in body_lower) or ('allotted' in body_lower and 'not allotted' not in body_lower):
                result['status'] = 'Allotted'
                
                # Try to extract quantity from "Alloted quantity : <number>" or variations
                quantity_match = re.search(r'(?:alloted|allotted)\s+quantity\s*:?\s*(\d+)', body_lower)
                if not quantity_match:
                    # Try other patterns
                    quantity_match = re.search(r'(\d+)\s*(?:kitta|shares?)', body_lower)
                
                if quantity_match:
                    result['quantity'] = int(quantity_match.group(1))
                else:
                    result['quantity'] = '?'
                
                result['message'] = f"Allotted {result['quantity']} shares" if result['quantity'] != '?' else "Allotted"
                self._log(f"Result: Allotted (quantity: {result['quantity']})")
            else:
                result['status'] = 'Unknown'
                result['quantity'] = '?'
                result['message'] = 'Unknown result'
                self._log(f"Result: Unknown - body text snippet: {body_lower[:200]}")
            
            return result
            
        except Exception as e:
            self._log(f"Error parsing result: {e}")
            return {
                'status': 'Error',
                'quantity': 0,
                'message': str(e)
            }
    
    def check_single_boid(self, boid: str, ipo_name: str) -> Dict:
        """
        Check IPO result for a single BOID.
        
        Returns result dict with status, quantity, message, error
        """
        max_attempts = 5
        
        for attempt in range(1, max_attempts + 1):
            try:
                self._log(f"Attempt {attempt}/{max_attempts} for BOID {boid}")
                
                # Small delay between attempts
                if attempt > 1:
                    time.sleep(2)
                
                # Solve captcha
                captcha_text = self.solve_captcha_with_retry()
                
                if not captcha_text:
                    self._log("Failed to solve captcha")
                    
                    # Check if it's due to rejection
                    if self.check_for_rejection():
                        return {
                            'status': 'Error',
                            'quantity': 0,
                            'message': 'Request rejected',
                            'error': 'REJECTED'
                        }
                    
                    # Reload page and try again
                    if attempt < max_attempts:
                        self.driver.get(self.BASE_URL)
                        time.sleep(3)
                        # Re-select IPO
                        # Note: This assumes IPO is already selected from the initial selection
                    continue
                
                # Submit
                success, status = self.submit_captcha(boid, captcha_text)
                
                if status == "rejected":
                    return {
                        'status': 'Error',
                        'quantity': 0,
                        'message': 'Request rejected',
                        'error': 'REJECTED'
                    }
                
                if not success and status == "invalid_captcha":
                    self._log(f"Captcha incorrect (attempt {attempt}/{max_attempts})")
                    # Page should auto-reload with new captcha
                    time.sleep(2)
                    continue
                
                # Success! Parse result
                if success and status == "success":
                    result = self.parse_result()
                    result['error'] = None
                    self._log(f"Parsed result: {result['status']} - {result['message']}")
                    return result
                else:
                    # Something went wrong
                    self._log(f"Unexpected status after submit: success={success}, status={status}")
                    if attempt < max_attempts:
                        self.driver.get(self.BASE_URL)
                        time.sleep(3)
                        continue
                    else:
                        return {
                            'status': 'Error',
                            'quantity': 0,
                            'message': f'Unexpected status: {status}',
                            'error': 'UNKNOWN_STATUS'
                        }
                
            except Exception as e:
                self._log(f"Error in attempt {attempt}: {e}")
                
                if attempt < max_attempts:
                    try:
                        self.driver.get(self.BASE_URL)
                        time.sleep(3)
                    except:
                        break
        
        # Failed after all attempts
        return {
            'status': 'Error',
            'quantity': 0,
            'message': 'Failed after max attempts',
            'error': 'MAX_ATTEMPTS'
        }
    
    def check_multiple_boids(self, boids: List[str], ipo_name: str) -> List[Dict]:
        """Check IPO result for multiple BOIDs."""
        results = []
        
        for idx, boid in enumerate(boids):
            print(f"\n{'='*70}")
            print(f"Checking BOID {idx + 1}/{len(boids)}: {boid}")
            print(f"{'='*70}")
            
            result = self.check_single_boid(boid, ipo_name)
            result['boid'] = boid
            results.append(result)
            
            # Check if we got rejected
            if result.get('error') == 'REJECTED':
                self.rejection_count += 1
                
                if self.rejection_count >= self.MAX_REJECTION_RETRIES:
                    print("\n⛔ Maximum rejection retries reached!")
                    print("MeroShare has blocked further requests.")
                    print("Please wait 15-30 minutes before trying again.")
                    break
                
                print(f"\n⚠️  Request rejected (retry {self.rejection_count}/{self.MAX_REJECTION_RETRIES})")
                print("Restarting browser and retrying...")
                
                # Restart browser
                self.close()
                time.sleep(5)
                self._init_driver()
                self.driver.get(self.BASE_URL)
                time.sleep(5)
                
                # Reset rejection count if retry succeeds
                result = self.check_single_boid(boid, ipo_name)
                result['boid'] = boid
                results[-1] = result  # Update result
                
                if result.get('error') != 'REJECTED':
                    self.rejection_count = 0  # Reset on success
            
            # Small delay between BOIDs
            if idx < len(boids) - 1:
                time.sleep(3)
        
        return results
    
    def display_results_table(self, ipo_name: str, results: List[Dict]):
        """Display results in a beautiful text table."""
        print(f"\n{'='*70}")
        print(f"IPO RESULT SUMMARY")
        print(f"{'='*70}\n")
        
        # Create table
        table = Texttable()
        table.set_cols_width([20, 15, 12, 30])
        table.set_cols_align(['l', 'c', 'c', 'l'])
        table.set_cols_dtype(['t', 't', 't', 't'])
        
        # Header row
        table.add_row([f"IPO: {ipo_name}", "", "", ""])
        table.add_row(["─" * 20, "─" * 15, "─" * 12, "─" * 30])
        table.add_row(["BOID", "Status", "Quantity", "Message"])
        
        # Data rows
        for result in results:
            boid = result.get('boid', 'Unknown')
            status = result.get('status', 'Unknown')
            quantity = result.get('quantity', 0)
            message = result.get('message', '')
            
            # Format quantity
            if status == 'Allotted':
                qty_str = str(quantity) if quantity != '?' else '?'
                status_emoji = '✅'
            elif status == 'Not Allotted':
                qty_str = '0'
                status_emoji = '❌'
            else:
                qty_str = '-'
                status_emoji = '⚠️'
            
            table.add_row([
                f"{boid[:6]}...{boid[-4:]}",  # Truncate BOID
                f"{status_emoji} {status}",
                qty_str,
                message[:28] if len(message) > 28 else message
            ])
        
        print(table.draw())
        print(f"\n{'='*70}\n")


def load_boids_from_env() -> List[str]:
    """Load BOID numbers from .env file."""
    load_dotenv()
    boid_str = os.getenv('BOID', '')
    
    if not boid_str:
        print("⚠️  No BOID found in .env file")
        return []
    
    # Split by comma and clean up
    boids = [boid.strip() for boid in boid_str.split(',') if boid.strip()]
    return boids


def main():
    parser = argparse.ArgumentParser(
        description="Enhanced IPO Result Checker - Multi-BOID with Beautiful Output"
    )
    
    parser.add_argument('--boid', type=str, help='BOID number (overrides .env)')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--auto', action='store_true', help='Auto-select first IPO (non-interactive)')
    
    args = parser.parse_args()
    
    # Banner
    print("\n" + "="*70)
    print("  IPO RESULT CHECKER - ENHANCED & AUTOMATED")
    print("  Powered by Custom CNN Model (73%+ Accuracy)")
    print("="*70 + "\n")
    
    # Load BOIDs
    if args.boid:
        boids = [args.boid]
        print(f"✓ Using BOID from command line: {args.boid}")
    else:
        boids = load_boids_from_env()
        if not boids:
            print("❌ No BOID provided!")
            print("\nPlease either:")
            print("  1. Add BOID to .env file (see .env.sample)")
            print("  2. Use --boid flag: python ipo_fully_auto_enhanced.py --boid 1301260001246310")
            return 1
        print(f"✓ Loaded {len(boids)} BOID(s) from .env file")
    
    # Initialize checker
    checker = EnhancedIPOChecker(debug=args.debug, headless=args.headless)
    
    try:
        # Start browser
        checker._init_driver()
        
        # Main loop - allows checking multiple IPOs
        while True:
            # Load page
            print("\nLoading IPO result page...")
            checker.driver.get(checker.BASE_URL)
            time.sleep(5)
            
            # Check for bot detection immediately after page load
            bot_check = checker.diagnose_bot_detection()
            if bot_check['detected']:
                print(f"\n❌ BOT DETECTION: {bot_check['reason']}")
                if bot_check['screenshot_path']:
                    print(f"   Screenshot saved: {bot_check['screenshot_path']}")
                print("\n⚠️  Troubleshooting:")
                print("   1. Don't use --headless mode")
                print("   2. Wait 15-30 minutes before trying again")
                print("   3. Check the screenshot to see what MeroShare is showing")
                return 1
            
            # Fetch available IPOs
            print("\nFetching available IPOs...")
            ipos = checker.get_available_ipos()
            
            if not ipos or len(ipos) == 0:
                print("❌ Could not fetch IPO list")
                # Check if it's bot detection
                bot_check = checker.diagnose_bot_detection()
                if bot_check['detected']:
                    print(f"\n⚠️  Reason: {bot_check['reason']}")
                    if bot_check['screenshot_path']:
                        print(f"   Screenshot: {bot_check['screenshot_path']}")
                return 1
            
            # Display IPO options
            print("\n" + "="*70)
            if len(ipos) == 1:
                print(f"Using IPO: {ipos[0]['text']}")
                print("="*70)
                choice_idx = 0
                selected_ipo = ipos[0]
            else:
                print("Available IPOs:")
                print("="*70)
                for idx, ipo in enumerate(ipos):
                    default_marker = " (default)" if ipo.get('isDefault') else ""
                    print(f"  {idx + 1}. {ipo['text']}{default_marker}")
                print("="*70)
                
                # Get user choice
                if args.auto:
                    # Auto-select first IPO (default)
                    choice_idx = 0
                    print(f"\n✓ Auto-selected: {ipos[0]['text']}")
                else:
                    # Interactive selection
                    while True:
                        try:
                            choice = input(f"\nSelect IPO (1-{len(ipos)}): ").strip()
                            choice_idx = int(choice) - 1
                            
                            if 0 <= choice_idx < len(ipos):
                                break
                            else:
                                print(f"Please enter a number between 1 and {len(ipos)}")
                        except (ValueError, KeyboardInterrupt, EOFError):
                            print("\n\nOperation cancelled by user")
                            return 1
                
                selected_ipo = ipos[choice_idx]
                print(f"\n✓ Selected: {selected_ipo['text']}")
                
                # SMART SELECTION: Only interact with dropdown if NOT choosing the already-selected default
                if selected_ipo.get('isDefault'):
                    print("  (Using default selection, no dropdown interaction needed)")
                else:
                    print(f"  (Changing selection to option {choice_idx + 1}...)")
                    # Use the actual DOM index from selected_ipo, not the filtered choice_idx
                    actual_dom_index = selected_ipo['index']
                    print(f"  [DEBUG] Clicking DOM index {actual_dom_index}")
                    if not checker.select_ipo(actual_dom_index):
                        print("❌ Failed to select IPO")
                        return 1
                    time.sleep(2)
                    print("  ✓ IPO selection completed")
            
            # Check results for all BOIDs
            print(f"\nChecking results for {len(boids)} BOID(s)...")
            results = checker.check_multiple_boids(boids, selected_ipo['text'])
            
            # Display results in table
            checker.display_results_table(selected_ipo['text'], results)
            
            # Summary
            allotted = sum(1 for r in results if r.get('status') == 'Allotted')
            not_allotted = sum(1 for r in results if r.get('status') == 'Not Allotted')
            errors = sum(1 for r in results if r.get('status') == 'Error')
            
            print(f"Summary: {allotted} allotted, {not_allotted} not allotted, {errors} errors")
            
            # Ask if user wants to check another IPO
            print("\n" + "="*70)
            try:
                continue_choice = input("Would you like to check the result again? (y/N): ").strip()
                
                if continue_choice.lower() == 'y':
                    print("\n🔄 Reloading page...\n")
                    time.sleep(2)
                    continue  # Restart the loop
                else:
                    print("\n✅ Exiting...")
                    return 0
                    
            except (KeyboardInterrupt, EOFError):
                print("\n\n✅ Exiting...")
                return 0
    
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        return 1
    
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1
    
    finally:
        print("\nClosing browser...")
        checker.close()
        print("✓ Done\n")


if __name__ == "__main__":
    exit(main())
