@echo off
setlocal enabledelayedexpansion

REM Tạo thư mục tạm nếu chưa có
if not exist "%temp%\BateParkingSystem" mkdir "%temp%\BateParkingSystem"

REM Tạo file VBScript để chạy ẩn
set "vbsfile=%temp%\BateParkingSystem\run_hidden.vbs"
echo Set WshShell = CreateObject("WScript.Shell") > "%vbsfile%"
echo WshShell.Run "pythonw.exe official-app.py", 0, False >> "%vbsfile%"

REM Khởi chạy VBScript và lập tức thoát
start /B "" wscript "%vbsfile%"

exit