# 🚀 Meroshare IPO Auto-Apply Bot

Automated IPO application tool for Meroshare (Nepal) that supports multiple accounts. Uses **REST API calls** — no browser required.

## ✨ Features

- **Multi-Account**: Apply across all accounts in one run
- **Telegram Bot**: Check open IPOs and trigger applications from your phone — [setup guide →](docs/telegram-bot.md)
- **Scheduled Auto-Apply**: Bot applies automatically every day; silent when nothing is open
- **No Browser Required**: Pure API, fast and reliable
- **Configurable**: Enable/disable accounts, control wait times and error handling

## 🛠️ Setup

### Prerequisites

- Python 3.10 or higher (required for modern type hint syntax)
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
   ```bash
   cp accounts.sample.json accounts.json
   ```
   Edit `accounts.json` with your credentials — see `accounts.sample.json` for all available fields.

   Key fields per account: `name`, `enabled`, `username`, `password`, `dp`, `crn`, `pin`

   Global settings: `wait_between_accounts_seconds`, `continue_on_account_failure`

   > **Telegram bot?** Add your `settings.telegram` block — see the [Telegram bot setup guide](docs/telegram-bot.md).

## 🚀 Usage

```bash
python run_accounts.py
```

This processes all enabled accounts sequentially, applies to open IPOs, and prints a summary.

## 📝 Tips

- Disable accounts by setting `"enabled": false` instead of deleting them
- Adjust `wait_between_accounts_seconds` if you hit rate limits
- Never commit `accounts.json` — it contains your credentials

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
