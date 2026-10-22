@echo off
title 7xwon Hizli Istek Paneli (Port 8083)
color 0A
echo ===================================================
echo   7xwon Canli POST Paneli Baslatiliyor...
echo   Adres: http://127.0.0.1:8083
echo ===================================================
cd /d "C:\Users\User\Desktop\7xwon_API"
python custom_post_runner.py
pause
