@echo off
setlocal
chcp 65001 >nul
title AKSHUKUR - DIGITAL CHRONICLE
cd /d "%~dp0"
if errorlevel 1 goto folder_error
where python >nul 2>nul
if errorlevel 1 goto python_error
python -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)"
if errorlevel 1 goto version_error
if not exist "app.py" goto files_error
if not exist "requirements.txt" goto files_error
if not exist "templates\index.html" goto files_error
if not exist "templates\base.html" goto files_error
if not exist "templates\oral-history.html" goto files_error
python -c "import flask" >nul 2>nul
if not errorlevel 1 goto start
choice /C YN /N /M "Flask is missing. Install requirements now? [Y/N]: "
if errorlevel 2 goto cancelled
python -m pip install -r requirements.txt
if errorlevel 1 goto install_error
:start
echo.
echo Home: http://127.0.0.1:5000/
echo 3D:   http://127.0.0.1:5000/rekonstrukciya
echo Stop: Ctrl+C
python app.py
if errorlevel 1 goto server_error
goto end
:folder_error
echo ERROR: Cannot open the project folder.
goto end
:python_error
echo ERROR: Python not found. Install Python 3.10+ and enable Add Python to PATH.
goto end
:version_error
echo ERROR: Python 3.10 or newer is required.
goto end
:files_error
echo ERROR: Extract the COMPLETE ZIP before running run.bat.
goto end
:install_error
echo ERROR: Installation failed. Check internet access and run:
echo python -m pip install -r requirements.txt
goto end
:server_error
echo ERROR: Server stopped with an error. Read the message above.
echo If port 5000 is busy, stop the other server and try again.
goto end
:cancelled
echo Cancelled. Install Flask before starting the server.
:end
echo.
pause
endlocal
