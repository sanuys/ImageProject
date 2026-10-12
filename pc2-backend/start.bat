@echo off
chcp 65001 >nul
title PC2 Backend (Flask) - port 5000
cd /d "%~dp0"

if not exist venv\Scripts\python.exe (
    echo [X] ยังไม่ได้ติดตั้ง library - รัน setup.bat ก่อน
    pause
    exit /b 1
)

echo ============================================================
echo   PC2 : BACKEND (Flask)  - http://0.0.0.0:5000
echo   ปิดเซิร์ฟเวอร์ด้วย Ctrl+C
echo ============================================================
echo.
venv\Scripts\python.exe app.py
pause
