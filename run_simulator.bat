@echo off
REM Toyota GR Racing Simulator - Windows Launch Script
REM ==================================================

echo.
echo ====================================================================
echo Toyota GR Racing Simulator
echo ====================================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.8+
    pause
    exit /b 1
)

echo Starting simulator...
echo.
echo The application will open at: http://127.0.0.1:8050
echo.
echo Press Ctrl+C to stop the server
echo ====================================================================
echo.

REM Run the simulator
python app.py

pause
