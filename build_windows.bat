@echo off
setlocal

python -m pip install --upgrade pip
python -m pip install pyinstaller
pyinstaller --onefile --name AdsPowerConsole adspower_web.py

echo.
echo Build complete: dist\AdsPowerConsole.exe
