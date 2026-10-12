@echo off
chcp 65001 >nul
title PC2 - ตรวจสอบการเชื่อมต่อไปยัง AI Server (PC3)
cd /d "%~dp0"

if not exist venv\Scripts\python.exe (
    echo [X] ยังไม่ได้ติดตั้ง library - รัน setup.bat ก่อน
    pause
    exit /b 1
)

echo ============================================================
echo   ทดสอบเส้นทาง  PC2 (เครื่องนี้)  ---^>  PC3 (AI Server)
echo   นี่คือเส้นทางจริงที่ระบบใช้ ถ้าผ่านที่นี่คือใช้งานได้แน่
echo ============================================================
echo.

venv\Scripts\python.exe check_ai.py 10.187.226.10 7860
pause
