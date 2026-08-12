@echo off
setlocal EnableExtensions

rem Run from repository root, even when launched by double-click.
cd /d "%~dp0"

if /I "%~1"=="help" (
    echo Usage: train_night_thermal.bat [s^|x] [epochs] [batch] [imgsz]
    echo Example CPU: train_night_thermal.bat s 100 1 640
    echo Example GPU: train_night_thermal.bat s 100 8 640
    exit /b 0
)

set "PYTHON=python"
if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"

set "MODEL=%~1"
if not defined MODEL set "MODEL=s"
set "EPOCHS=%~2"
if not defined EPOCHS set "EPOCHS=100"
set "BATCH=%~3"
if not defined BATCH set "BATCH=1"
set "IMGSZ=%~4"
if not defined IMGSZ set "IMGSZ=640"

if /I not "%MODEL%"=="s" if /I not "%MODEL%"=="x" (
    echo ERROR: model harus s atau x.
    exit /b 2
)

if not exist "model\yolo26%MODEL%.pt" (
    echo ERROR: model\yolo26%MODEL%.pt tidak ditemukan.
    exit /b 3
)

%PYTHON% -c "import sys; print('Python:', sys.executable)"
if errorlevel 1 (
    echo ERROR: Python tidak ditemukan atau tidak bisa dijalankan.
    exit /b 4
)

%PYTHON% scripts\train_night_thermal.py --model "%MODEL%" --epochs "%EPOCHS%" --batch "%BATCH%" --imgsz "%IMGSZ%" --workers 0 --device cpu
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if "%EXIT_CODE%"=="0" (
    echo Training selesai. Artefak ada di model\best-night-thermal.*
) else (
    echo Training gagal dengan exit code %EXIT_CODE%.
)
pause
exit /b %EXIT_CODE%
