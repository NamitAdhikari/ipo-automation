# Running the Bot as a Background Service

The bot auto-starts on login, restarts on crash, and stops cleanly on shutdown.  
Pick the guide for your OS.

---

## macOS — launchd

**1. Edit the plist**  
Open `ipobot.plist` and replace every `/CHANGE/ME/ApplyIPO` with the absolute path to your `ApplyIPO` folder.

**2. Install and start**
```bash
cp scripts/ipobot.plist ~/Library/LaunchAgents/com.user.ipobot.plist
launchctl load ~/Library/LaunchAgents/com.user.ipobot.plist
```

**3. Verify it's running**
```bash
launchctl list | grep ipobot
# Should show a PID (not a dash) in the first column
```

**Manage**
```bash
# Stop
launchctl unload ~/Library/LaunchAgents/com.user.ipobot.plist

# Restart
launchctl unload ~/Library/LaunchAgents/com.user.ipobot.plist && \
launchctl load   ~/Library/LaunchAgents/com.user.ipobot.plist

# Logs
tail -f /tmp/ipobot.log
tail -f /tmp/ipobot.err
```

> **If your project folder is inside `Documents`, `Downloads`, or `Desktop`:**  
> macOS blocks background processes from accessing those folders by default.  
> Go to **System Settings → Privacy & Security → Full Disk Access** and add `/bin/bash`.

---

## Linux — systemd

**1. Edit the service file**  
Open `ipobot.service` and replace both `/CHANGE/ME/ApplyIPO` paths with your actual path.

**2. Install and start**
```bash
mkdir -p ~/.config/systemd/user
cp scripts/ipobot.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now ipobot
```

**3. Verify it's running**
```bash
systemctl --user status ipobot
```

**Manage**
```bash
# Stop / Restart
systemctl --user stop ipobot
systemctl --user restart ipobot

# Logs (live)
journalctl --user -u ipobot -f
```

> **Headless server (no desktop session)?**  
> Run `loginctl enable-linger $USER` once so the service starts without a GUI login.

---

## Windows — Startup folder

**1. Edit the bat file**  
Open `start-bot.bat` and set `PROJECT_DIR` to the full path of your `ApplyIPO` folder.

**2. Add to startup**  
Press `Win+R`, type `shell:startup`, hit Enter — then copy `start-bot.bat` into that folder.

The bot will start on next login. If it crashes, it restarts automatically after 10 seconds.

**To stop the bot:** open Task Manager → find `python.exe` or `start-bot.bat` → End task.
