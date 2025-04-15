@echo off
setlocal enabledelayedexpansion

:: 询问是否生成数据
set "generate="
set /p "generate=Do you want to generate new test data? [y/n]: "

:: 转换为小写处理
if /i "!generate!"=="y" (
    echo Cleaning data folder...
    if exist data (
        rd /s /q data
    )
    mkdir data
    
    echo Generating test data...
    data_generator.exe
    
    if errorlevel 1 (
        echo Data generation failed!
        pause
        exit /b 1
    )
)

:: 运行测试程序
echo Starting evaluation...
python check.py

pause