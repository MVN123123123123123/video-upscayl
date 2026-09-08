@echo off
rem ==============================================================================
rem  Video-Upscayl - One-Click Windows Launcher (GUI Mode)
rem  Launches the graphical user interface without opening a black command window
rem ==============================================================================

cd /d "%~dp0"

rem Check for pythonw in active virtualenv
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" -m video_upscaler
    exit /b 0
)

rem Check for python in active virtualenv
if exist ".venv\Scripts\python.exe" (
    start "" ".venv\Scripts\python.exe" -m video_upscaler
    exit /b 0
)

rem Check for system pythonw
where pythonw >nul 2>nul
if %ERRORLEVEL% equ 0 (
    start "" pythonw -m video_upscaler
    exit /b 0
)

rem Check for system python
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    start "" python -m video_upscaler
    exit /b 0
)

echo [ERROR] Python was not found in your system PATH or local .venv directory.
echo Please install Python from https://www.python.org/downloads/
echo Make sure to check "Add Python to PATH" during installation.
pause
exit /b 1
