@echo off
cd /d "%~dp0"
chcp 65001 > nul
title 브런치 자동 좋아요 - EXE 단일 실행파일 빌드

echo ====================================================
echo  브런치 자동 좋아요 GUI 실행파일(EXE) 생성 도구
echo ====================================================
echo.

set PYTHON_CMD=python
if exist ".venv\Scripts\python.exe" set PYTHON_CMD=.venv\Scripts\python.exe
if exist "venv\Scripts\python.exe" set PYTHON_CMD=venv\Scripts\python.exe

echo [*] PyInstaller 설치 확인 중...
%PYTHON_CMD% -m pip install pyinstaller

echo [*] EXE 빌드를 시작합니다...
%PYTHON_CMD% -m PyInstaller --noconfirm --onedir --windowed --name "BrunchLikeTool" --add-data "brunch_api.py;." --add-data "browser_bot.py;." --add-data "scheduler.py;." gui.py

if errorlevel 1 (
    echo [!] 빌드 실패.
) else (
    echo [*] 빌드 성공! dist\BrunchLikeTool 폴더를 확인하세요.
)
pause
