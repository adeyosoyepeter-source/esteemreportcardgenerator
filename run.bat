@echo off
REM Report Card Generator - Quick Start Script for Windows

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo ===================================
echo Report Card Generator - Django App
echo ===================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r django_app\requirements.txt

REM Run migrations
echo Setting up database...
python manage.py migrate

REM Collect static files
echo Collecting static files...
python manage.py collectstatic --noinput

echo.
echo Setup complete!
echo.
echo Starting Django development server...
echo The app will be available at: http://127.0.0.1:8000
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start the server
python manage.py runserver

pause
