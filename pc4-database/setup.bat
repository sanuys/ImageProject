@echo off
chcp 65001 >nul
title PC4 Database - ติดตั้ง library
cd /d "%~dp0"

echo ============================================================
echo   PC4 : DATABASE SERVER  - ติดตั้ง library
echo ============================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [X] ไม่พบ Python บนเครื่องนี้
    echo     ติดตั้งจาก https://www.python.org/downloads/
    echo     ตอนติดตั้งอย่าลืมติ๊ก "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

for /f "delims=" %%v in ('python --version') do echo พบ %%v
echo.

if not exist venv (
    echo [1/3] สร้าง virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [X] สร้าง venv ไม่สำเร็จ
        pause
        exit /b 1
    )
) else (
    echo [1/3] มี venv อยู่แล้ว - ข้าม
)

echo [2/3] อัปเกรด pip...
venv\Scripts\python.exe -m pip install --upgrade pip --quiet

echo [3/3] ติดตั้ง library จาก requirements.txt...
venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [X] ติดตั้งไม่สำเร็จ - ตรวจสอบว่าเครื่องนี้ต่ออินเทอร์เน็ตอยู่
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   [OK] ติดตั้งเสร็จแล้ว
echo   ถ้ามีฐานข้อมูลเดิม ก๊อป database.db มาวางในโฟลเดอร์นี้
echo   ขั้นต่อไป: ดับเบิลคลิก start.bat
echo ============================================================
pause
