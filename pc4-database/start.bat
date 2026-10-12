@echo off
chcp 65001 >nul
title PC4 Database Server - port 5100
cd /d "%~dp0"

if not exist venv\Scripts\python.exe (
    echo [X] ยังไม่ได้ติดตั้ง library - รัน setup.bat ก่อน
    pause
    exit /b 1
)

echo ============================================================
echo   PC4 : DATABASE SERVER  - http://0.0.0.0:5100
echo   ต้องเปิดเครื่องนี้เป็นเครื่องแรกเสมอ
echo   ปิดเซิร์ฟเวอร์ด้วย Ctrl+C
echo ============================================================
echo.
venv\Scripts\python.exe db_server.py
pause
