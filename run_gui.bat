@echo off
cd /d "%~dp0"
chcp 65001 > nul
title 브런치 자동 좋아요 (GUI)

echo ====================================================
echo  브런치 연재글 자동 좋아요 도구 (GUI)
echo ====================================================
echo.

set PYTHON_CMD=python
if exist ".venv\Scripts\python.exe" set PYTHON_CMD=.venv\Scripts\python.exe
if exist "venv\Scripts\python.exe" set PYTHON_CMD=venv\Scripts\python.exe

%PYTHON_CMD% gui.py

if errorlevel 1 (
    echo.
    echo [안내] 실행 중 오류가 발생했습니다. 먼저 setup.bat을 실행해보세요.
    pause
)
