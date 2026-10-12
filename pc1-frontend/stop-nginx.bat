@echo off
chcp 65001 >nul
title PC1 Nginx - หยุดการทำงาน

set NGINX_DIR=C:\nginx

if not exist "%NGINX_DIR%\nginx.exe" (
    echo [X] ไม่พบ Nginx ที่ %NGINX_DIR%
    pause
    exit /b 1
)
cd /d "%NGINX_DIR%"

nginx.exe -s stop
echo [OK] สั่งหยุด Nginx แล้ว
timeout /t 2 >nul
tasklist /fi "imagename eq nginx.exe" | find /i "nginx.exe" >nul
if not errorlevel 1 (
    echo [!] ยังมี nginx.exe ค้างอยู่ - สั่งปิดแบบบังคับ
    taskkill /f /im nginx.exe
)
pause
