#!/usr/bin/env python3
"""
Live Captcha Collection Script
Collects and labels real captchas from MeroShare for training dataset improvement
"""

import os
import sys
import time
import numpy as np
import cv2
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from PIL import Image
from captcha_inference_advanced import CaptchaInferenceAdvanced
import argparse

# Initialize the model globally
solver = None

def init_model():
    """Initialize the captcha solver model"""
    global solver
    if solver is None:
        print("Loading captcha model...")
        solver = CaptchaInferenceAdvanced()
        print("✓ Model loaded\n")

def predict_captcha(image_array):
    """Wrapper function to predict captcha from numpy array"""
    global solver
    if solver is None:
        init_model()
    result = solver.predict(image_array, strategy='best', num_attempts=7)
    return result['result'], result['confidence'], len(result['all_attempts'])

def setup_browser(headless=False):
    """Setup Chrome browser with minimal stealth options"""
    chrome_options = webdriver.ChromeOptions()
    
    # Minimal stealth - only essential options
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    if headless:
        chrome_options.add_argument('--headless')
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def refresh_captcha(driver, debug=False):
    """Refresh captcha without reloading the page"""
    try:
        # XPATH for captcha refresh button
        refresh_xpath = "/html/body/app-root/app-allotment-result/div/div/div/div/form/div[2]/div[2]/div/div[2]/button[2]"
        
        # Find and click the refresh button
        button = driver.find_element(By.XPATH, refresh_xpath)
        button.click()
        
        # Wait for new captcha to load
        time.sleep(2)
        
        if debug:
            print("✓ Captcha refreshed")
        
        return True
    except Exception as e:
        if debug:
            print(f"⚠️ Could not refresh captcha: {e}")
        return False

def capture_captcha(driver, save_path, debug=False):
    """Capture captcha image from the page using element screenshot"""
    try:
        # Wait for page to fully load (only needed on first load)
        time.sleep(1)
        
        # Try multiple possible selectors for the captcha image
        selectors = [
            "img[alt='Captcha']",
            "img[alt='captcha']",
            ".captcha-image img",
            "#captchaImage",
            "img[src*='captcha']",
        ]
        
        captcha_img = None
        for selector in selectors:
            try:
                captcha_img = driver.find_element(By.CSS_SELECTOR, selector)
                if debug:
                    print(f"✓ Found captcha with selector: {selector}")
                    print(f"  Captcha src: {captcha_img.get_attribute('src')[:100]}")
                break
            except:
                continue
        
        if not captcha_img:
            if debug:
                print("❌ Could not find captcha with any known selector")
            raise Exception("Captcha image not found")
        
        # Use element screenshot (like the main script does)
        # Wait a bit for captcha to fully load
        time.sleep(0.5)
        
        # Get screenshot as PNG bytes
        captcha_png = captcha_img.screenshot_as_png
        
        # Convert PNG bytes to numpy array
        nparr = np.frombuffer(captcha_png, np.uint8)
        img_array = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if debug:
            print(f"  Captured captcha shape: {img_array.shape}")
        
        # Save as PNG
        cv2.imwrite(save_path, img_array)
        
        return img_array
        
    except Exception as e:
        print(f"❌ Error capturing captcha: {e}")
        if debug:
            import traceback
            traceback.print_exc()
        return None

def calculate_brightness(img_array):
    """Calculate average brightness of captcha image from numpy array"""
    try:
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
        else:
            gray = img_array
        avg_brightness = np.mean(gray)
        return avg_brightness
    except:
        return 0

def collect_samples(num_samples=10, headless=False, debug=False):
    """Collect and label live captcha samples"""
    
    # Create live dataset directory
    dataset_dir = "captcha_dataset_live"
    os.makedirs(dataset_dir, exist_ok=True)
    
    print(f"\n{'='*60}")
    print(f"🎯 Live Captcha Collection Script")
    print(f"{'='*60}")
    print(f"📊 Target: {num_samples} samples")
    print(f"💾 Save location: {dataset_dir}/")
    print(f"\n{'='*60}\n")
    
    driver = None
    collected = 0
    skipped = 0
    
    try:
        driver = setup_browser(headless=headless)
        
        # Load page once at the start
        print("Loading MeroShare page...")
        driver.get("https://iporesult.cdsc.com.np/")
        time.sleep(3)  # Wait for initial page load
        print("✓ Page loaded\n")
        
        for i in range(num_samples):
            print(f"\n[{i+1}/{num_samples}] Collecting sample...")
            
            # Refresh captcha instead of reloading page (except first iteration)
            if i > 0:
                if not refresh_captcha(driver, debug=debug):
                    print("⚠️ Could not refresh captcha, reloading page...")
                    driver.get("https://iporesult.cdsc.com.np/")
                    time.sleep(3)
            
            # Generate temporary filename
            temp_path = f"temp_captcha_{int(time.time()*1000)}.png"
            
            # Capture captcha (returns numpy array)
            img_array = capture_captcha(driver, temp_path, debug=debug)
            
            if img_array is None:
                print("⚠️ Failed to capture captcha, retrying...")
                continue
            
            # Get model prediction
            predicted_text, confidence, attempts = predict_captcha(img_array)
            brightness = calculate_brightness(img_array)
            
            # Show prediction
            print(f"🤖 Model prediction: {predicted_text} (confidence: {confidence:.2f}, attempts: {attempts})")
            print(f"📊 Brightness: {brightness:.2f}")
            
            if not headless:
                print(f"👁️  Check the captcha in the browser window")
            
            # Get actual value from user
            actual_value = input("✏️  Enter the CORRECT captcha value (or press Enter to skip): ").strip()
            
            if not actual_value:
                print("⏭️  Skipped")
                os.remove(temp_path)
                skipped += 1
                continue
            
            # Validate input
            if len(actual_value) != 5 or not actual_value.isdigit():
                print("⚠️ Invalid input (must be 5 digits). Skipping...")
                os.remove(temp_path)
                skipped += 1
                continue
            
            # Save with correct label
            final_path = os.path.join(dataset_dir, f"{actual_value}_{int(time.time()*1000)}.png")
            os.rename(temp_path, final_path)
            
            # Show result
            if actual_value == predicted_text:
                print(f"✅ CORRECT! Model predicted correctly")
            else:
                print(f"❌ WRONG (model: {predicted_text}, actual: {actual_value})")
            
            print(f"💾 Saved: {final_path}")
            collected += 1
            
            # Brief pause before next sample
            time.sleep(0.5)
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Collection interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if debug:
            import traceback
            traceback.print_exc()
    finally:
        if driver:
            driver.quit()
        
        # Clean up any leftover temp files
        for f in os.listdir('.'):
            if f.startswith('temp_captcha_') and f.endswith('.png'):
                try:
                    os.remove(f)
                except:
                    pass
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 COLLECTION SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Collected: {collected} samples")
    print(f"⏭️  Skipped: {skipped} samples")
    print(f"💾 Total in dataset: {len([f for f in os.listdir(dataset_dir) if f.endswith('.png')])}")
    print(f"📁 Location: {dataset_dir}/")
    print(f"{'='*60}\n")
    
    # Show next steps
    total_samples = len([f for f in os.listdir(dataset_dir) if f.endswith('.png')])
    
    if total_samples >= 50:
        print("💡 TIP: You have enough samples to retrain!")
        print("\nNext steps:")
        print("  1. uv run python generate_augmented_dataset.py --combine")
        print("  2. uv run python train_captcha_model_improved.py")
        print("  3. uv run python test_live_quick.py 10  # Test new model\n")
    elif total_samples >= 20:
        print(f"💡 TIP: Collect {50 - total_samples} more samples for optimal retraining\n")
    else:
        print(f"💡 TIP: Collect at least {50 - total_samples} more samples before retraining\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collect live captcha samples for training")
    parser.add_argument("num_samples", type=int, nargs='?', default=10, 
                       help="Number of samples to collect (default: 10)")
    parser.add_argument("--headless", action="store_true", 
                       help="Run in headless mode")
    parser.add_argument("--debug", action="store_true", 
                       help="Enable debug output")
    
    args = parser.parse_args()
    
    collect_samples(args.num_samples, args.headless, args.debug)
