# 🚀 Meroshare IPO Auto-Apply Bot

Automated IPO application bot for Meroshare (Nepal) that supports multiple accounts. This tool automatically applies for IPOs on your behalf using **REST API calls** instead of browser automation - making it faster, more reliable, and requiring no browser installation.

## 📋 What It Does

This automation bot:
- Logs into your Meroshare account(s) automatically via API
- Fetches available IPO listings
- Intelligently selects the optimal number of units (kitta) to apply for
- Fills out and submits IPO application forms
- Supports running multiple accounts sequentially
- Provides detailed progress feedback with rich terminal output

## ✨ Features

- **API-Based**: Uses REST API calls instead of browser automation (faster & more reliable)
- **No Browser Required**: Works without Chrome or any browser installed
- **Multi-Account Support**: Run IPO applications for multiple accounts in one go
- **Smart Unit Selection**: Automatically determines the optimal number of units to apply for
- **Rich Console Output**: Beautiful terminal UI with progress indicators and summaries
- **Error Handling**: Continues processing remaining accounts even if one fails
- **Configurable**: Control wait times and error handling behavior
- **Account Management**: Enable/disable specific accounts without removing their configuration

## 🛠️ Setup

### Prerequisites

- Python 3.10 or higher
- Valid Meroshare account credentials

### Installation

1. **Clone or download this project**

2. **Install Python dependencies**
   ```bash
   # Using uv (recommended)
   uv venv -p 3.10
   uv pip install -r requirements.txt

   # Or using pip
   pip install -r requirements.txt
   ```

3. **Configure your accounts**
   `accounts.json` is used for running on multiple accounts. `.env` file is only used for running on single account. Since, this is primarily focused on running on multiple accounts, ignoring setting up `.env`. Create an `accounts.json` file based on `accounts.sample.json`:
   ```bash
   cp accounts.sample.json accounts.json
   ```
   
   Edit `accounts.json` with your Meroshare credentials:
   ```json
   {
     "accounts": [
       {
         "name": "John's Account",
         "enabled": true,
         "credentials": {
           "username": "your_username",
           "password": "your_password",
           "dp": "13700",
           "crn": "your_crn",
           "pin": "your_pin"
         }
       }
     ],
     "settings": {
       "wait_between_accounts_seconds": 5,
       "continue_on_account_failure": true
     }
   }
   ```

### Configuration Fields

**Account Fields:**
- `name`: Friendly name for the account (for identification)
- `enabled`: Set to `true` to include this account, `false` to skip
- `username`: Your Meroshare username
- `password`: Your Meroshare password
- `dp`: Your DP (Depository Participant) code
- `crn`: Your CRN (Client Registration Number)
- `pin`: Your transaction PIN

**Global Settings:**
- `wait_between_accounts_seconds`: Delay between processing accounts (in seconds)
- `continue_on_account_failure`: Continue with remaining accounts if one fails - `true` or `false`

## 🚀 Usage

### Multi-Account Mode (Recommended)

Run IPO applications for all enabled accounts:

```bash
python run_multi_account_api.py
```

OR with `uv`:
```bash
uv run run_multi_account_api.py
```

### Single Account Mode

For single account usage, create a `.env` file:
```bash
cp .env.sample .env
# Edit .env with your credentials
```

Then run:
```bash
python main_api.py
```

This will:
1. Display a summary of all configured accounts
2. Process each enabled account sequentially
3. Wait the configured time between accounts
4. Show a final summary of results

### Output

The script provides rich terminal output including:
- Account summary table before processing
- Real-time progress for each account
- Success/failure status for each account
- Final summary table with results

Example:
```
🚀 Meroshare IPO Auto-Apply Bot (API) 🚀

📋 Account Summary

#     Account Name    DP      Status
1     John's Account  13700   ✓ Enabled
2     Jane's Account  12600   ✓ Enabled

→ 2 account(s) enabled

🚀 Starting IPO applications for enabled accounts...

🏃 Running Account 1/2
John's Account
Username: john123
DP: 13700

[Processing...]

✅ Account 1 completed successfully

⏳ Waiting 5 seconds before next account...

📊 FINAL SUMMARY

#     Account Name      Result
1     John's Account    ✅ Success
2     Jane's Account    ✅ Success

Total: 2 accounts | Success: 2 | Failed: 0
```

## 🔧 Legacy Selenium Version

The original Selenium-based automation scripts are still available:
- `main_improved.py` - Single account (Selenium)
- `run_multi_account.py` - Multi-account (Selenium)

These require Chrome browser but may be useful for debugging or if the API changes.

## 🧪 Manual Testing with Playwright

For verifying the flow manually using a browser, use the included test script:

```bash
# Install playwright and browsers
pip install playwright
playwright install chromium

# Run the test script with your credentials
python test_with_playwright.py
```

The test script will:
1. Load credentials from `.env` or `accounts.json`
2. Open a browser and login to Meroshare
3. Navigate to IPO listing
4. Test logout functionality
5. Display a summary of results

## 📝 Tips

- **API-based is faster**: The API version completes in seconds vs minutes for Selenium
- **Disable accounts** by setting `enabled: false` instead of deleting them
- **Adjust wait times** if you experience rate limiting
- **Keep credentials secure** - never commit `accounts.json` to version control

## ⚠️ Important Notes

- This tool is for personal use only
- Ensure you have the legal right to automate your Meroshare account
- Keep your `accounts.json` file secure and never share it
- Make sure you have sufficient balance in your accounts before running

## 🐛 Troubleshooting

**Login fails:**
- Verify your credentials in `accounts.json`
- Check if the DP code is correct (numeric code like 13700)

**API errors:**
- Check your internet connection
- Meroshare API might be temporarily down
- Your account credentials may have changed

**Application fails:**
- Verify you have sufficient balance
- Check if IPO is still open for application
- Ensure your account is eligible for the IPO

## 📄 License

For personal use only.

---

**Disclaimer:** Use this tool responsibly. The authors are not responsible for any issues arising from the use of this automation tool.
