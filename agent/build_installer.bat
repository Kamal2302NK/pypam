@echo off
setlocal
title Build TNeGA PAM Agent installer
cd /d "%~dp0"

echo ==============================================================
echo   Building TNeGA PAM Agent  (PyInstaller + Inno Setup)
echo ==============================================================

where python >nul 2>nul || (echo [ERROR] Python 3 must be installed on the BUILD PC only. & pause & exit /b 1)

echo [1/4] Installing PyInstaller...
python -m pip install --quiet --upgrade pyinstaller || (echo [ERROR] pip failed & pause & exit /b 1)

echo [2/4] Preparing icon...
if not exist pypam.ico (
    python -m pip install --quiet pillow
    python -c "from PIL import Image; Image.open(r'..\static\img\tnega_logo.png').convert('RGBA').save('pypam.ico', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])" || (echo [ERROR] icon conversion failed & pause & exit /b 1)
)

echo [3/4] Building PyPAM-Agent.exe ...
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name PyPAM-Agent --icon pypam.ico pypam_agent.py || (echo [ERROR] PyInstaller failed & pause & exit /b 1)

echo [4/4] Building installer...
set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
    echo.
    echo [!] Inno Setup 6 not found. Install it:  winget install JRSoftware.InnoSetup
    echo     The portable agent is ready at: %~dp0dist\PyPAM-Agent.exe
    pause
    exit /b 0
)
if not exist ffmpeg.exe echo [i] Tip: put ffmpeg.exe in this folder to bundle screen recording into the installer.
"%ISCC%" installer.iss || (echo [ERROR] Inno Setup failed & pause & exit /b 1)

echo.
echo ==============================================================
echo   DONE:  %~dp0dist\PyPAM-Agent-Setup.exe
echo   Copy it to the server:  /opt/pypam/agent/dist/PyPAM-Agent-Setup.exe
echo   Users then download it from  My Assets  -> Desktop Agent.
echo ==============================================================
pause
