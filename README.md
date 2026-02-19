# IPO Result Checker - Automated with CNN Captcha Solver

Fully automated IPO result checker for MeroShare (iporesult.cdsc.com.np) with custom-trained CNN model for captcha solving.

## Features

- ✅ **73.7% Captcha Accuracy** - Custom CNN model trained on live MeroShare captchas
- ✅ **Multi-BOID Support** - Check multiple BOIDs in one run
- ✅ **Beautiful Table Output** - Clean, formatted results display
- ✅ **Smart IPO Selection** - Interactive dropdown or auto-select mode
- ✅ **Auto-Retry Logic** - Handles request rejections and browser restarts
- ✅ **Bot Detection Alerts** - Detects and warns when MeroShare blocks automation
- ⚠️ **Headless Mode Available** - But not recommended (triggers bot detection)
- ✅ **Low Bot Detection** - Minimal stealth options for natural browsing in visible mode

## Quick Start

### Prerequisites

- **Python 3.12.5** with `uv` package manager
- **Chrome browser** installed
- **Virtual environment** at `/Users/namit/Documents/Projects/MMP/automations/.venv`
- **Pre-trained model** - See "Getting the Model" below

### Installation

**Install dependencies:**
```bash
cd "/Users/namit/Documents/Projects/MMP/automations/IPO Result"
uv pip install -r requirements.txt
```

Or if using standard pip:
```bash
pip install -r requirements.txt
```

### Getting the Model

The trained model files (`.h5`) are **NOT** in git (90MB is too large). You have two options:

**Option 1: Get the pre-trained model**
- Download `captcha_model_v2.h5` from [your cloud storage link]
- Place in `captcha_model/` directory
- Config file `config_v2.json` is already in git

**Option 2: Train from scratch (Recommended for first setup)**
```bash
# Generate augmented dataset from committed training data
uv run python generate_augmented_dataset.py --combine

# Train model (takes ~10-20 minutes)
uv run python train_captcha_model_improved.py

# This creates captcha_model_v2.h5 automatically
```

The training datasets are already in git, so you can train immediately after cloning!

### Step 1: Configure Your BOIDs

Edit the `.env` file in the project root:

```bash
# Single BOID
BOID=xxxxxxxxxxxxxx

# Multiple BOIDs (comma-separated)
BOID=xxxxxxxxxxxxxx,yyyyyyyyyyyyyyy
```

### Step 2: Run the Script

**Option A: Multi-BOID Mode (Recommended)**

Check all BOIDs from `.env` with interactive IPO selection:
```bash
cd "/Users/namit/Documents/Projects/MMP/automations/IPO Result"
uv run python ipo_fully_auto_enhanced.py
```

**Option B: Single BOID Mode**

Check a specific BOID (overrides .env):
```bash
uv run python ipo_fully_auto_enhanced.py --boid xxxxxxxxxxxxxx
```

**Option C: Auto Mode (Non-Interactive)**

Automatically select the first available IPO:
```bash
uv run python ipo_fully_auto_enhanced.py --auto
```

**Option D: Debug Mode**

See detailed logs and keep browser open:
```bash
uv run python ipo_fully_auto_enhanced.py --debug
```

**Option E: Headless Mode (⚠️ Not Recommended)**

Run without opening a visible browser window:
```bash
uv run python ipo_fully_auto_enhanced.py --headless
```

⚠️ **Warning:** Headless mode often triggers bot detection on MeroShare. Use visible browser mode for reliability.

**Combine options:**
```bash
# Single BOID + auto-select (without headless - more reliable)
uv run python ipo_fully_auto_enhanced.py --boid xxxxxxxxxxxxxx --auto
```

### Step 3: Interpret Results

The script will display a formatted table:

```
╔════════════════════╦════════════════════════════╦════════════════╗
║ BOID               ║ IPO                        ║ Status         ║
╠════════════════════╬════════════════════════════╬════════════════╣
║ xxxxxxxxxxxxxx   ║ Suryakunda Hydro Electric  ║ Allotted: 10   ║
║ yyyyyyyyyyyyyyy   ║ Suryakunda Hydro Electric  ║ Not Allotted   ║
╚════════════════════╩════════════════════════════╩════════════════╝
```

**Possible Statuses:**
- ✅ `Allotted: X` - You received X shares
- ❌ `Not Allotted` - Sorry, no shares allotted
- ⚠️ `Error: [message]` - Technical issue (captcha failed, request rejected, etc.)

## Project Structure

```
IPO Result/
├── ipo_fully_auto_enhanced.py     # Main script (multi-BOID + IPO selection)
├── test_live_quick.py             # Data collection for model improvement
├── captcha_inference_advanced.py  # CNN inference engine
├── train_captcha_model_improved.py # Model training script
├── generate_augmented_dataset.py  # Data augmentation
│
├── captcha_model/
│   ├── captcha_model_v2.h5        # Trained model (73.7% accuracy)
│   └── config_v2.json             # Model configuration
│
├── captcha_dataset/               # Original 350 labeled samples
├── captcha_dataset_live/          # 119 live collected samples
│
├── .env                           # Your BOIDs configuration
└── .env.sample                    # Template
```

## How It Works

### Process Flow

1. **Browser Launch** - Opens Chrome with minimal stealth options
2. **Page Load** - Navigates to iporesult.cdsc.com.np
3. **IPO Selection** - Shows available IPOs and lets you choose (or auto-picks first)
4. **Captcha Capture** - Takes screenshot of captcha image
5. **CNN Prediction** - Uses trained model with 7 augmentation attempts
6. **Form Submission** - Enters BOID and predicted captcha text
7. **Result Detection** - Parses response for allotment status:
   - ✅ **Success:** "Congratulation Alloted !!! Alloted quantity : X"
   - ❌ **Failure:** "Sorry, not alloted for the entered BOID."
   - 🔁 **Retry:** Invalid captcha → restart from step 2
   - ⚠️ **Error:** Request rejected → wait and restart

### Detection Logic

The script correctly handles MeroShare's typos:
- Checks for both "alloted" (one 't') and "allotted"
- Checks for both "Congratulation" (no 's') and "Congratulations"
- Detection order: Request rejection → Success → Captcha error → Unknown

### Browser Stealth

Uses **minimal stealth options** to avoid bot detection:
```python
--disable-blink-features=AutomationControlled
excludeSwitches: ["enable-automation"]
useAutomationExtension: False
```

**What we DON'T do** (these trigger detection):
- ❌ CDP commands (Page.addScriptToEvaluateOnNewDocument)
- ❌ User agent spoofing
- ❌ Excessive Chrome options
- ❌ Repeated dropdown interactions

## Model Performance

- **Full sequence accuracy:** 73.7%
- **Per-digit accuracy:** 94.7%
- **Expected attempts per success:** ~1.4 attempts
- **Training data:** 350 original + 119 live samples → 5,600 augmented

## Important Notes

### Model & Data Management
**What's in git:**
- ✅ Training datasets: `captcha_dataset/` (350 samples) and `captcha_dataset_live/` (119 samples)
- ✅ Model configuration files (`config_v2.json`)
- ✅ All Python scripts
- ✅ `.env.sample` template

**What's NOT in git:**
- ❌ Trained model files: `captcha_model/*.h5` (90MB - too large for git)
- ❌ Augmented dataset: `captcha_dataset_augmented/` (regenerable from originals)
- ❌ Your `.env` file (contains your BOIDs - keep private)

**Why this setup?**
- Training datasets (~11MB) are reasonable for git and needed for retraining
- Model files (90MB) are too large - share via cloud storage or retrain locally
- Augmented dataset can be regenerated anytime with `generate_augmented_dataset.py`

### Rate Limiting ⚠️
MeroShare blocks IPs after too many attempts:
- **Max safe attempts:** 2-3 runs within 15 minutes
- **Cooldown period:** 15-30 minutes if blocked
- **Symptoms:** "Request rejected" popup, TSBrPFrame iframe
- **Prevention:** Space out your runs, use `--auto` mode

### Bot Detection Prevention
The script uses **minimal stealth** to avoid detection:

**What we DO:**
```python
--disable-blink-features=AutomationControlled
excludeSwitches: ["enable-automation"]
useAutomationExtension: False
```

**What we DON'T do** (these trigger detection):
- ❌ CDP commands (Page.addScriptToEvaluateOnNewDocument)
- ❌ User agent spoofing
- ❌ Excessive Chrome options
- ❌ Repeated dropdown interactions

**Best practices:**
- ✅ Use visible browser mode (not `--headless`)
- ✅ Use default IPO selection (option 1) whenever possible
- ✅ Use `--auto` flag for non-interactive mode
- ✅ Don't run script repeatedly in short periods
- ✅ Wait 15+ minutes between sessions

**Why headless mode doesn't work:**
- MeroShare detects headless browsers through various fingerprinting techniques
- Bot detection check automatically saves screenshot to `/tmp/bot_detection_*.png`
- The screenshot shows MeroShare's blocking page instead of the IPO form
- **Recommendation:** Always use visible browser mode for production use

### MeroShare Quirks
The site has some typos that the script handles:
- Uses "alloted" (one 't') instead of "allotted"
- Uses "Congratulation" (no 's') instead of "Congratulations"
- Detection logic accounts for both spellings

### Model Versioning
- Keep old model versions as backups
- Current: `captcha_model_v2.h5` (73.7% accuracy)
- After retraining: `captcha_model_v3.h5`, `v4.h5`, etc.
- Test before deploying: `uv run python test_live_quick.py 10`

## Improving Model Accuracy

### Current Performance
- **Training accuracy:** 99.71% per-digit, 98.78% full-sequence
- **Live accuracy:** 73.7% full-sequence, 94.7% per-digit
- **Expected attempts:** ~1.4 attempts per success

### How to Add More Training Data

**Step 1: Collect live samples**

```bash
# Collect 20 samples (recommended for first run)
uv run python test_live_quick.py 20
```

**What happens during collection:**
1. Browser opens and loads MeroShare
2. Model predicts the captcha and shows its guess in terminal
3. You look at the captcha in the browser
4. You type the CORRECT 5-digit number (what you see, not what model predicted)
5. Script saves the image with YOUR label as: `{your_label}_{timestamp}.png`
6. Repeat for all samples

**Example session:**
```
[1/20] Collecting sample...
🤖 Model prediction: 14239 (confidence: 0.85, attempts: 2)
📊 Brightness: 189.23
👁️  Check the captcha in the browser window
✏️  Enter the CORRECT captcha value (or press Enter to skip): 14239
✅ CORRECT! Model predicted correctly
💾 Saved: captcha_dataset_live/14239_1771413562852.png

[2/20] Collecting sample...
🤖 Model prediction: 67823 (confidence: 0.62, attempts: 3)
📊 Brightness: 223.45
👁️  Check the captcha in the browser window
✏️  Enter the CORRECT captcha value (or press Enter to skip): 67328
❌ WRONG (model: 67823, actual: 67328)
💾 Saved: captcha_dataset_live/67328_1771413565123.png
```

**Important tips:**
- **Double-check before pressing Enter** - Wrong labels hurt accuracy
- **Press Enter to skip** unclear/unreadable captchas
- **Focus on edge cases** - Very bright (220+) or dark (160-) captchas
- **Collect at least 50 samples** before retraining for best results

**Step 2: Retrain the model**

Once you have 50+ live samples:

```bash
# Step 1: Combine original + live datasets and augment
uv run python generate_augmented_dataset.py --combine

# Step 2: Retrain model (creates captcha_model_v3.h5)
uv run python train_captcha_model_improved.py

# Step 3: Test new model
uv run python test_live_quick.py 10
```

**Expected improvements after 100-200 live samples:**
- Full-sequence accuracy: 70-80% (up from 73.7%)
- Attempts needed: 1.2-1.4 (down from 1.4)

### Retraining Options

**Option A: Combine Original + Live (Recommended)**
```bash
uv run python generate_augmented_dataset.py --combine
```
Uses both 350 original samples + your live samples for best results.

**Option B: Live Samples Only**
```bash
uv run python generate_augmented_dataset.py --source captcha_dataset_live
```

**Option C: Custom Directories**
```bash
uv run python generate_augmented_dataset.py --source captcha_dataset captcha_dataset_live other_dataset
```

## Advanced Usage

### Command-Line Arguments

**ipo_fully_auto_enhanced.py (Main Script)**
```bash
--boid BOID         # Check specific BOID (overrides .env, comma-separated for multiple)
--debug             # Enable debug output, keep browser open
--headless          # Run without browser GUI
--auto              # Auto-select first IPO (non-interactive, safer for automation)
```

**Examples:**
```bash
# Check all BOIDs from .env
uv run python ipo_fully_auto_enhanced.py

# Check single BOID
uv run python ipo_fully_auto_enhanced.py --boid xxxxxxxxxxxxxx

# Check multiple BOIDs (override .env)
uv run python ipo_fully_auto_enhanced.py --boid xxxxxxxxxxxxxx,yyyyyyyyyyyyyyy

# Auto-select first IPO + headless
uv run python ipo_fully_auto_enhanced.py --auto --headless

# Debug mode (keep browser open)
uv run python ipo_fully_auto_enhanced.py --debug
```

**test_live_quick.py (Data Collection)**
```bash
num_samples         # Number of samples to collect (default: 10)
--debug             # Show detailed capture information
--headless          # Run without browser GUI (⚠️ may trigger bot detection)
```

**Examples:**
```bash
# Collect 20 samples (with visible browser - recommended)
uv run python test_live_quick.py 20

# Collect with debug output
uv run python test_live_quick.py 10 --debug
```

### Configuration Files

**.env** - Your BOID configuration
```bash
# Single BOID
BOID=xxxxxxxxxxxxxx

# Multiple BOIDs (comma-separated, no spaces)
BOID=xxxxxxxxxxxxxx,yyyyyyyyyyyyyyy
```

**captcha_model/config_v2.json** - Model architecture
```json
{
  "input_shape": [50, 200, 1],
  "num_digits": 5,
  "num_classes": 10,
  "model_version": "v2"
}
```

### Running in Production

⚠️ **Note:** Headless mode frequently triggers bot detection. For automated runs, use visible browser with `--auto` flag.

**Scheduled task with visible browser (Recommended):**
```bash
# Run every hour with visible browser (more reliable)
0 * * * * cd "/Users/namit/Documents/Projects/MMP/automations/IPO Result" && DISPLAY=:0 /path/to/uv run python ipo_fully_auto_enhanced.py --auto >> /tmp/ipo_results.log 2>&1
```

**Cron job example:**
```bash
# Check every 2 hours (to avoid rate limiting)
0 */2 * * * cd "/Users/namit/Documents/Projects/MMP/automations/IPO Result" && /path/to/uv run python ipo_fully_auto_enhanced.py --auto >> /tmp/ipo_results.log 2>&1
```

**Important for automation:**
- ✅ Use `--auto` flag (non-interactive)
- ⚠️ Avoid `--headless` (triggers bot detection)
- ✅ Run max every 2 hours to avoid rate limits
- ✅ Set `DISPLAY=:0` for visible browser in cron jobs

### Dataset Management

**Backup datasets before retraining:**
```bash
cp -r captcha_dataset_live captcha_dataset_live_backup_$(date +%Y%m%d)
```

**Check dataset statistics:**
```bash
# Count samples
ls captcha_dataset_live/*.png | wc -l

# Check augmented dataset
ls captcha_dataset_augmented/*.png | wc -l
```

**Clean old datasets:**
```bash
# Remove augmented dataset (regenerate anytime)
rm -rf captcha_dataset_augmented/

# Keep original and live datasets!
```

## Troubleshooting

### Quick Diagnosis

Run this command to diagnose issues:
```bash
uv run python ipo_fully_auto_enhanced.py --debug
```

**Check these in order:**

1. **Bot Detection?** Look for `/tmp/bot_detection_*.png` screenshot
   - If exists → Bot detection triggered
   - Solution: Remove `--headless`, wait 15-30 min

2. **IP Blocked?** Look for "Request rejected" in output
   - Solution: Wait 15-30 minutes

3. **Invalid Captcha?** Model prediction wrong repeatedly
   - Solution: Collect more samples, retrain model

4. **No IPOs?** Only showing 1 IPO
   - This is normal - only 1 IPO available currently

---

### Request Rejected / IP Blocked
**Symptoms:** "Request rejected" popup, TSBrPFrame iframe, or browser shows blocking message

**Cause:** MeroShare rate limiting - too many attempts in short period

**Solution:** 
- Wait 15-30 minutes for cooldown
- Reduce frequency: max 2-3 runs per 15 minutes
- Use `--auto` flag to minimize interactions

### Invalid Captcha Repeatedly
**Cause:** Model accuracy needs improvement OR very bright/dark captchas

**Solution:**
1. Check captcha brightness in debug mode: `--debug`
2. Collect more edge case samples: `uv run python test_live_quick.py 50`
3. Retrain model with combined datasets
4. Test new model before deployment

### Only 1 IPO Showing
**Cause:** Only 1 IPO currently available on MeroShare

**Solution:** This is normal behavior - script will use the default IPO

### Bot Detection Triggered (Including Headless Mode Issues)
**Symptoms:** 
- "Could not fetch IPO list" error
- Page won't load properly
- Blank page or missing form elements
- Repeated failures

**Cause:** Bot detection triggered by:
- Headless mode (most common)
- Too much automation activity
- Excessive dropdown interactions
- Rate limiting

**How to verify if bot detection is triggered:**
1. **Check debug screenshots:** Look in `/tmp/` for `bot_detection_*.png` files (auto-saved)
2. **Check console output** for these messages:
   ```
   ⚠️  BOT DETECTION: Found 'request rejected' in page
   ⚠️  BOT DETECTION: Missing form elements (captcha=False, ng-select=False)
   ```
3. **Run with debug flag** to see page details:
   ```bash
   uv run python ipo_fully_auto_enhanced.py --debug
   ```

**Solution:** 
- **Remove `--headless` flag** - Headless mode often triggers detection
  ```bash
  # Instead of:
  uv run python ipo_fully_auto_enhanced.py --headless --auto
  
  # Use:
  uv run python ipo_fully_auto_enhanced.py --auto
  ```
- Use `--auto` flag to pick default IPO (no dropdown interaction)
- Wait 15-30 minutes before trying again
- Reduce run frequency (max 2-3 runs per 15 minutes)
- Check `/tmp/bot_detection_*.png` to see what MeroShare is showing

### Detection Logic Issues
**Problem:** Script says "Invalid captcha" when result shows "Sorry not allotted"

**Status:** ✅ FIXED in both scripts

**How it was fixed:**
- Changed detection order: Check rejection → Success → Captcha error
- Now correctly identifies "Sorry not allotted" as SUCCESS (captcha solved correctly)
- Handles MeroShare typos: "alloted" (one 't'), "Congratulation" (no 's')

### Model Version Issues
**Problem:** Validation accuracy dropped after retraining

**Solution:**
- Keep old model versions (`captcha_model_v2.h5`, `v3.h5`, etc.)
- Test new model with: `uv run python test_live_quick.py 10`
- If worse, revert to previous version
- Check if live samples were labeled correctly

## Environment

- **Python:** 3.12.5 (managed by uv)
- **Virtual env:** `/Users/namit/Documents/Projects/MMP/automations/.venv`
- **Package manager:** uv
- **Browser:** Chrome (auto-managed by Selenium)

## Files Configuration

- **.env** - Your BOIDs (comma-separated)
- **.gitignore** - Excludes sensitive files and datasets
- **captcha_model/config_v2.json** - Model architecture config

## Success Rate & Performance

Based on current model v2 (73.7% accuracy):
- **1st attempt success:** 73.7%
- **2nd attempt success:** 94.2% cumulative
- **3rd attempt success:** 98.1% cumulative
- **Average attempts needed:** ~1.4

**Within MeroShare's rate limits** (2-3 attempts per 15 minutes)

### Performance Metrics

**Training Performance:**
- Training accuracy: 99.71% per-digit, 98.78% full-sequence
- Training samples: 350 original + 119 live = 469 → 5,600 augmented

**Live Performance:**
- Live accuracy: 73.7% full-sequence, 94.7% per-digit
- TTA (Test-Time Augmentation): 7 attempts per captcha
- Average prediction time: ~2-3 seconds

**Expected Improvements After Retraining:**
- With 100 live samples: 75-80% full-sequence
- With 200 live samples: 80-85% full-sequence
- Target: 85%+ (1.2 attempts needed)

## Contributing

To improve the model:
1. Collect more live samples with `test_live_quick.py`
2. Label them correctly in `captcha_dataset_live/`
3. Run retraining workflow
4. Test new model accuracy

## License

For personal use only. MeroShare terms of service apply.

---

**Note:** This tool automates form submission on MeroShare. Use responsibly and respect rate limits to avoid IP blocks.
