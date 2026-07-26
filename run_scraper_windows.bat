@echo off
REM ==================================================================
REM  Numberblocks catalog builder - Windows one-click runner
REM  Double-click this file. It installs yt-dlp (if needed) and
REM  builds catalog.json next to it.
REM ==================================================================
cd /d "%~dp0"

echo Checking for Python...
python --version >nul 2>&1
if errorlevel 1 (
  echo.
  echo Python is not installed. Get it from https://www.python.org/downloads/
  echo During install, TICK "Add Python to PATH".
  echo.
  pause
  exit /b 1
)

echo Installing / updating yt-dlp...
python -m pip install -U yt-dlp

echo.
echo Building catalog...
python build_catalog.py

echo.
echo Done. catalog.json is in this folder.
pause
