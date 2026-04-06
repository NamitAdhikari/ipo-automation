# 🚀 Meroshare IPO Auto-Apply Bot

Automated IPO application bot for Meroshare (Nepal) that supports multiple accounts. This tool automatically applies for IPOs on your behalf, handling the entire application process from login to submission.

## 📋 What It Does

This automation bot:
- Logs into your Meroshare account(s) automatically
- Fetches available IPO listings
- Intelligently selects the optimal number of units (kitta) to apply for
- Fills out and submits IPO application forms
- Supports running multiple accounts sequentially
- Provides detailed progress feedback with rich terminal output

## ✨ Features

- **Multi-Account Support**: Run IPO applications for multiple accounts in one go
- **Smart Unit Selection**: Automatically determines the optimal number of units to apply for
- **Rich Console Output**: Beautiful terminal UI with progress indicators and summaries
- **Error Handling**: Continues processing remaining accounts even if one fails
- **Configurable**: Control headless mode, wait times, and error handling behavior
- **Account Management**: Enable/disable specific accounts without removing their configuration

## 🛠️ Setup

### Prerequisites

- Python 3.8 or higher
- Chrome browser installed
- Valid Meroshare account credentials

### Installation

1. **Clone or download this project**

2. **Install Python (3.12+) dependencies**
   ```bash
   uv venv -p 3.12
   uv pip install -r requirements.txt
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
       "headless": false,
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
- `headless`: Run browser in headless mode (no GUI) - `true` or `false`
- `wait_between_accounts_seconds`: Delay between processing accounts (in seconds)
- `continue_on_account_failure`: Continue with remaining accounts if one fails - `true` or `false`

## 🚀 Usage

### Multi-Account Mode (Recommended)

Run IPO applications for all enabled accounts:

```bash
python run_multi_account.py
```

OR with `uv`:
```bash
uv run run_multi_account.py
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
🚀 Meroshare IPO Auto-Apply Bot 🚀

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

## 📝 Tips

- **Test with headless: false** initially to watch the automation and ensure everything works
- **Set headless: true** for faster, unattended operation
- **Disable accounts** by setting `enabled: false` instead of deleting them
- **Adjust wait times** if you experience rate limiting
- **Keep credentials secure** - never commit `accounts.json` to version control

## ⚠️ Important Notes

- This tool is for personal use only
- Ensure you have the legal right to automate your Meroshare account
- Keep your `accounts.json` file secure and never share it
- The bot requires Chrome browser to be installed
- Make sure you have sufficient balance in your accounts before running

## 🐛 Troubleshooting

**Browser not found:**
- Ensure Chrome is installed on your system

**Login fails:**
- Verify your credentials in `accounts.json`
- Check if the DP code is correct

**Timeout errors:**
- Check your internet connection
- Meroshare website might be slow or down

**Application fails:**
- Verify you have sufficient balance
- Check if IPO is still open for application
- Ensure your account is eligible for the IPO

## 📄 License

For personal use only.

---

**Disclaimer:** Use this tool responsibly. The authors are not responsible for any issues arising from the use of this automation tool.
