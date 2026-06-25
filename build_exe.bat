@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo  VectorCAST - Windows EXE Build
echo ============================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not on PATH.
    exit /b 1
)

echo [1/3] Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller>=6.0

echo.
echo [2/3] Building executable...
python -m PyInstaller --noconfirm VectorCAST.spec

if errorlevel 1 (
    echo.
    echo BUILD FAILED.
    exit /b 1
)

echo.
echo [3/3] Done!
echo.
echo Your application is ready:
echo   dist\VectorCAST\VectorCAST.exe
echo.
echo Copy the entire "dist\VectorCAST" folder to share or install the app.
echo Double-click VectorCAST.exe to launch.
echo.
pause
