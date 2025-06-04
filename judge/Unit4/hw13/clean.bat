@echo off
setlocal

REM --- Configuration ---
set results_DIR=results
set TEST_CASES_DIR=test_cases
REM --- End Configuration ---

echo ======================================
echo  Directory Cleanup Utility
echo ======================================
echo.
echo This script will attempt to delete the following directories and all their contents:
echo   - %results_DIR%
echo   - %TEST_CASES_DIR%
echo.

:CONFIRM
set /p "CHOICE=Are you sure to clean the data? (y/n): "
if /i "%CHOICE:~0,1%"=="Y" goto DELETE_DIRS
if /i "%CHOICE:~0,1%"=="N" goto CANCELLED
echo Invalid input. Please enter 'y' or 'n'.
goto CONFIRM

:DELETE_DIRS
echo.
echo Proceeding with cleanup...
echo.

if exist "%results_DIR%" (
    echo Deleting directory: %results_DIR%
    rd /s /q "%results_DIR%"
    if errorlevel 1 (
        echo ERROR: Failed to delete %results_DIR%. It might be in use or permissions are insufficient.
    ) else (
        echo Successfully deleted %results_DIR%.
    )
) else (
    echo Directory %results_DIR% not found. Skipping.
)
echo.

if exist "%TEST_CASES_DIR%" (
    echo Deleting directory: %TEST_CASES_DIR%
    rd /s /q "%TEST_CASES_DIR%"
    if errorlevel 1 (
        echo ERROR: Failed to delete %TEST_CASES_DIR%. It might be in use or permissions are insufficient.
    ) else (
        echo Successfully deleted %TEST_CASES_DIR%.
    )
) else (
    echo Directory %TEST_CASES_DIR% not found. Skipping.
)
echo.
echo Cleanup process finished.
goto END

:CANCELLED
echo.
echo Cleanup cancelled by user.
goto END

:END
echo.
pause
endlocal