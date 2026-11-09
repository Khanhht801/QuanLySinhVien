@echo off
cd /d "%~dp0"
start "" "%~dp0.venv\Scripts\pyqt5-tools.exe" designer "%~dp0main.ui"
