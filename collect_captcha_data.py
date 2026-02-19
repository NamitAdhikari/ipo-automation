"""
Data Collection Tool for Captcha Training
==========================================

This tool helps you quickly collect labeled captcha samples for training.

Usage:
1. Run this script
2. Browser opens to the IPO result page
3. Captcha is displayed
4. Type the 5 digits you see and press Enter
5. Captcha is saved with label
6. New captcha is automatically loaded
7. Repeat until you have 150-200 samples

Press 'q' + Enter to quit
Press 's' + Enter to skip a captcha if unclear
"""

import cv2
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from datetime import datetime

# Configuration
CAPTCHA_DIR = "captcha_dataset"
CHROME_DRIVER_PATH = "/opt/homebrew/bin/chromedriver"
TARGET_URL = "https://iporesult.cdsc.com.np"

def setup_driver():
    """Initialize Chrome driver"""
    options = Options()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    driver.maximize_window()
    return driver

def get_captcha_image(driver):
    """Screenshot the captcha image"""
    try:
        # Wait for captcha to load
        captcha_img = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "img[alt='captcha']"))
        )
        
        # Wait a bit more for image to fully render
        time.sleep(0.5)
        
        # Method 1: Try to get screenshot of element directly
        try:
            png = captcha_img.screenshot_as_png  # This is a method call
            import numpy as np
            from PIL import Image
            import io
            
            img = Image.open(io.BytesIO(png))
            img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            
            # Check if image is valid (not just black/dark)
            if img_cv.mean() > 10:  # If average pixel value > 10, it's not just black
                print("  ✓ Using element screenshot method")
                return img_cv
        except Exception as e:
            print(f"  Element screenshot failed: {e}, trying full page method...")
            pass
        
        # Method 2: Screenshot full page and crop
        # Scroll element into view first
        driver.execute_script("arguments[0].scrollIntoView(true);", captcha_img)
        time.sleep(0.3)
        
        # Get captcha location and size
        location = captcha_img.location
        size = captcha_img.size
        
        # Take full page screenshot
        png = driver.get_screenshot_as_png()
        
        # Convert to opencv image
        import numpy as np
        from PIL import Image
        import io
        
        img = Image.open(io.BytesIO(png))
        img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        
        # Get pixel ratio (for retina displays)
        pixel_ratio = driver.execute_script("return window.devicePixelRatio")
        
        # Crop to captcha area (accounting for pixel ratio)
        x = int(location['x'] * pixel_ratio)
        y = int(location['y'] * pixel_ratio)
        w = int(size['width'] * pixel_ratio)
        h = int(size['height'] * pixel_ratio)
        
        captcha_crop = img_cv[y:y+h, x:x+w]
        
        return captcha_crop
    except Exception as e:
        print(f"Error getting captcha: {e}")
        import traceback
        traceback.print_exc()
        return None

def refresh_captcha(driver):
    """Click the refresh button to get a new captcha"""
    try:
        refresh_button = driver.find_element(By.XPATH, 
            "/html/body/app-root/app-allotment-result/div/div/div/div/form/div[2]/div[2]/div/div[2]/button[2]")
        refresh_button.click()
        time.sleep(1)  # Wait for new captcha to load
        return True
    except Exception as e:
        print(f"Error refreshing captcha: {e}")
        return False

def save_captcha(image, label, captcha_dir):
    """Save captcha with label"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{label}_{timestamp}.png"
    filepath = os.path.join(captcha_dir, filename)
    cv2.imwrite(filepath, image)
    return filename

def collect_data():
    """Main data collection loop"""
    # Create dataset directory
    os.makedirs(CAPTCHA_DIR, exist_ok=True)
    
    # Count existing samples
    existing = len([f for f in os.listdir(CAPTCHA_DIR) if f.endswith('.png')])
    
    print("="*70)
    print("CAPTCHA DATA COLLECTION TOOL")
    print("="*70)
    print(f"\nDataset directory: {CAPTCHA_DIR}")
    print(f"Existing samples: {existing}")
    print(f"Target: 150-200 samples")
    print("\nInstructions:")
    print("  - Type the 5 digits you see")
    print("  - Press Enter to save and get next captcha")
    print("  - Type 'q' + Enter to quit")
    print("  - Type 's' + Enter to skip unclear captchas")
    print("  - Type 'r' + Enter to refresh if captcha doesn't load")
    print("\n" + "="*70)
    
    input("\nPress Enter to start...")
    
    # Setup browser
    print("\nLaunching browser...")
    driver = setup_driver()
    
    try:
        driver.get(TARGET_URL)
        print("Loaded IPO result page")
        time.sleep(3)  # Wait for page to fully load
        
        collected = 0
        skipped = 0
        
        while True:
            # Get current captcha
            captcha_img = get_captcha_image(driver)
            
            if captcha_img is None:
                print("Failed to get captcha. Type 'r' to refresh or 'q' to quit.")
                user_input = input("> ").strip().lower()
                if user_input == 'q':
                    break
                elif user_input == 'r':
                    refresh_captcha(driver)
                continue
            
            # Check if image looks valid
            if captcha_img.shape[0] < 10 or captcha_img.shape[1] < 10:
                print(f"⚠️  Captcha too small ({captcha_img.shape}). Refreshing...")
                refresh_captcha(driver)
                continue
            
            if captcha_img.mean() < 10:
                print("⚠️  Captcha appears black/empty. Refreshing...")
                refresh_captcha(driver)
                continue
            
            # Display captcha (in a window)
            display_img = cv2.resize(captcha_img, (captcha_img.shape[1]*4, captcha_img.shape[0]*4))
            cv2.imshow('Current Captcha', display_img)
            cv2.waitKey(1)
            
            # Get label from user
            print(f"\n[Sample {existing + collected + 1}] ", end='')
            user_input = input("Enter the 5 digits you see: ").strip()
            
            # Handle special commands
            if user_input.lower() == 'q':
                print("\nQuitting...")
                break
            elif user_input.lower() == 's':
                print("Skipped")
                skipped += 1
                refresh_captcha(driver)
                continue
            elif user_input.lower() == 'r':
                print("Refreshing captcha...")
                refresh_captcha(driver)
                continue
            
            # Validate input
            if len(user_input) != 5 or not user_input.isdigit():
                print(f"Invalid input '{user_input}'. Must be exactly 5 digits. Try again.")
                continue
            
            # Save captcha with label
            filename = save_captcha(captcha_img, user_input, CAPTCHA_DIR)
            collected += 1
            print(f"✓ Saved as {filename}")
            print(f"Progress: {existing + collected} total ({collected} this session, {skipped} skipped)")
            
            # Refresh for next captcha
            if not refresh_captcha(driver):
                print("Failed to refresh. Press Enter to try again...")
                input()
                refresh_captcha(driver)
            
            time.sleep(0.5)
        
        # Cleanup
        cv2.destroyAllWindows()
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()
        print("\n" + "="*70)
        print("DATA COLLECTION SUMMARY")
        print("="*70)
        print(f"Collected this session: {collected}")
        print(f"Skipped: {skipped}")
        print(f"Total in dataset: {existing + collected}")
        print(f"Target remaining: {max(0, 150 - (existing + collected))}")
        print(f"\nDataset location: {os.path.abspath(CAPTCHA_DIR)}")
        print("="*70)

if __name__ == "__main__":
    collect_data()
