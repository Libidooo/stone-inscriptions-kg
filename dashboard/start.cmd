@echo off
title Buddhist Inscription KG Dashboard
cd /d "%~dp0"

echo ============================================
echo   Buddhist Inscription Knowledge Graph
echo   Starting dashboard...
echo ============================================
echo.

python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Python found, starting server...
    start "" http://localhost:8080
    timeout /t 1 /nobreak >nul
    python -m http.server 8080
    goto end
)

node --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Node.js found, starting server...
    start "" http://localhost:8080
    npx serve . -p 8080
    goto end
)

echo [ERROR] Please install Python 3 first
echo Download: https://www.python.org/downloads/
echo (Check "Add Python to PATH" during install)
echo.
pause
exit /b

:end
echo Server stopped.
pause
