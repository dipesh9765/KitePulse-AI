@echo off
title KitePulse AI - Launch All
color 0e
echo ===================================================
echo          KitePulse AI - Full System Launcher
echo ===================================================
cd /d "%~dp0"

echo [*] Launching Backend Server in a new window...
start "KitePulse AI Backend" cmd /k "cd /d "%~dp0backend" && start_backend.bat"

echo [*] Launching Frontend Dev Server in a new window...
start "KitePulse AI Frontend" cmd /k "cd /d "%~dp0frontend" && start_frontend.bat"

echo ===================================================
echo [OK] Both Backend and Frontend services started!
echo - Backend API: http://127.0.0.1:8000
echo - Frontend UI: http://127.0.0.1:5173
echo ===================================================
timeout /t 3
exit
