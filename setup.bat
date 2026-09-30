@echo off
cd /d "%~dp0"
chcp 65001 > nul
title 브런치 자동 좋아요 도구 - 환경 설정

echo ====================================================
echo  브런치 자동 좋아요 도구 - 의존성 자동 설치
echo ====================================================
echo.

set PYTHON_CMD=python
if exist ".venv\Scripts\python.exe" set PYTHON_CMD=.venv\Scripts\python.exe
if exist "venv\Scripts\python.exe" set PYTHON_CMD=venv\Scripts\python.exe

echo [*] Python 패키지를 설치합니다...
%PYTHON_CMD% -m pip install --upgrade pip
%PYTHON_CMD% -m pip install -r requirements.txt

echo.
echo [*] 바탕화면에 최신 바로가기 아이콘을 생성/갱신합니다...
powershell -ExecutionPolicy Bypass -File "%~dp0create_shortcut.ps1"

if errorlevel 1 (
    echo.
    echo [!] 설치 중 오류가 발생했습니다. 파이썬 설치 여부를 확인해주세요.
) else (
    echo.
    echo [*] 모든 필수 라이브러리 설치 및 바탕화면 바로가기 생성이 완료되었습니다!
)
pause