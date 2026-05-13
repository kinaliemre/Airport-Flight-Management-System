@echo off
cd /d "%~dp0"
echo Airport Flight Management System baslatiliyor...
echo.
echo Site adresi: http://127.0.0.1:5000/
echo Sunucuyu kapatmak icin bu pencerede CTRL+C tuslayin.
echo.
start "" http://127.0.0.1:5000/
python -m flask --app app run --host 127.0.0.1 --port 5000 --debug
pause
