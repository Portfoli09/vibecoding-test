@echo off
cd /d "%~dp0"
set "PY=python"
if exist "C:\Python313\python.exe" set "PY=C:\Python313\python.exe"
echo [%date% %time%] start > run_log.txt
"%PY%" --version >> run_log.txt 2>&1
"%PY%" -c "import pygame" >> run_log.txt 2>&1
if errorlevel 1 (
  echo Installing pygame...
  "%PY%" -m pip install pygame >> run_log.txt 2>&1
)
echo Starting game...
"%PY%" shooting.py >> run_log.txt 2>&1
echo exit code %errorlevel% >> run_log.txt
if errorlevel 1 (
  type run_log.txt
  pause
)
