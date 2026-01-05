@echo off
REM EVE LI XML Generator - Windows Batch File
REM 
REM Usage Examples:
REM   run_eve_xml.bat test     - Test API connection
REM   run_eve_xml.bat vfz      - Process VFZ only
REM   run_eve_xml.bat pe       - Process PE only  
REM   run_eve_xml.bat both     - Process both (default)
REM   run_eve_xml.bat schedule - Run scheduler mode

set PYTHON_EXE=C:\Users\svdleer\Documents\Python\Git\li\.venv\Scripts\python.exe
set SCRIPT_DIR=%~dp0
set MODE=%1

if "%MODE%"=="" set MODE=both

echo Starting EVE LI XML Generator in %MODE% mode...
echo.

cd /d "%SCRIPT_DIR%"

"%PYTHON_EXE%" eve_li_xml_generator.py --mode %MODE%

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Processing failed with exit code %ERRORLEVEL%
    pause
    exit /b %ERRORLEVEL%
) else (
    echo.
    echo SUCCESS: Processing completed successfully
)

if "%MODE%"=="schedule" (
    echo Press Ctrl+C to stop the scheduler
    pause
)

echo.
pause
