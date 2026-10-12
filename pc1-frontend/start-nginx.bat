@echo off
chcp 65001 >nul
title PC1 Nginx - port 80

set NGINX_DIR=C:\nginx

if not exist "%NGINX_DIR%\nginx.exe" (
    echo [X] ไม่พบ Nginx ที่ %NGINX_DIR%
    echo     โหลดจาก https://nginx.org/en/download.html แล้วแตกไฟล์ไว้ที่ C:\nginx
    echo     ถ้าวางไว้ที่อื่น ให้แก้บรรทัด "set NGINX_DIR=" ในไฟล์นี้
    pause
    exit /b 1
)

cd /d "%NGINX_DIR%"

echo [1/2] ตรวจสอบไฟล์ config...
nginx.exe -t
if errorlevel 1 (
    echo.
    echo [X] config ผิด - แก้ให้ผ่านก่อนถึงจะ start ได้
    echo     ดูบรรทัดที่ error บอกด้านบน มักเป็นเรื่อง path ของ root
    pause
    exit /b 1
)

echo.
echo [2/2] เริ่ม Nginx...
tasklist /fi "imagename eq nginx.exe" | find /i "nginx.exe" >nul
if not errorlevel 1 (
    echo   Nginx รันอยู่แล้ว - สั่งโหลด config ใหม่แทน
    nginx.exe -s reload
) else (
    start "" nginx.exe
)

echo.
echo ============================================================
echo   [OK] Nginx ทำงานแล้ว - เปิด http://localhost ดูได้เลย
echo   หยุดด้วย stop-nginx.bat
echo ============================================================
pause
