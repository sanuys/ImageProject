@echo off
chcp 65001 >nul
title ImageProject - Single PC
cd /d "%~dp0"

if not exist venv\Scripts\python.exe (
    echo [X] ยังไม่ได้ติดตั้ง library - ดับเบิลคลิก setup.bat ก่อน
    pause
    exit /b 1
)

venv\Scripts\python.exe run_single_pc.py
pause
