@echo off
setlocal enabledelayedexpansion

set "gen_data="
set /p "gen_data=generate new data?(y/n): "

if /i "!gen_data!"=="y" (
    echo.
    if exist data rd /s /q data
    if exist out rd /s /q out
    mkdir data >nul 2>&1
    mkdir out >nul 2>&1
    data_generator.exe
    echo.
) 

echo Judge begin...
echo.
python check.py

echo.
echo Judge end.
echo.
pause