@echo off
:: start-bot.bat — Windows startup script for bot.py
:: ====================================================
:: SETUP (one-time):
::   1. Edit PROJECT_DIR below to your actual ApplyIPO folder path.
::   2. Open the Startup folder:
::        Press Win+R → type: shell:startup → Enter
::   3. Copy this file (or create a shortcut to it) inside that folder.
::
:: BEHAVIOUR:
::   - Runs on login (via Startup folder)
::   - If bot.py crashes, the loop restarts it automatically after 10s
::   - Closes when you shut down Windows (as intended)
::   - Runs minimized in a background console window
::
:: USEFUL:
::   To stop the bot, find "start-bot.bat" or "python" in Task Manager
::   and end the process.

set PROJECT_DIR=C:\CHANGE\ME\ApplyIPO

cd /d "%PROJECT_DIR%"

:loop
echo [%date% %time%] Starting bot...
"%PROJECT_DIR%\.venv\Scripts\python.exe" "%PROJECT_DIR%\bot.py"
echo [%date% %time%] Bot exited. Restarting in 10 seconds...
timeout /t 10 /nobreak >nul
goto loop
