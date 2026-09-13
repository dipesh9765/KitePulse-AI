@echo off
title KitePulse AI - Frontend Client
color 0a
echo ===================================================
echo           KitePulse AI - Frontend Web App
echo ===================================================
cd /d "%~dp0"

REM Check if node_modules exists
if not exist "node_modules" (
    echo [*] node_modules not found. Running npm install...
    call npm install
)

echo [*] Starting Vite Frontend on http://127.0.0.1:5173...
call npm run dev -- --host 127.0.0.1 --port 5173

pause
