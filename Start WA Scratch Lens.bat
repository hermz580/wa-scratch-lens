@echo off
cd /d "%~dp0"
start "WA Scratch Lens Server" /min python server.py
ping 127.0.0.1 -n 3 >nul
start "" http://127.0.0.1:8879
