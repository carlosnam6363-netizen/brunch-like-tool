@echo off
cd /d "%~dp0"
chcp 65001 > nul
title 브런치 자동 좋아요 - 아침 06~08시 자동 실행 에이전트

echo ====================================================
echo  브런치 자동 좋아요 - 매일 아침 자동 실행 에이전트
echo ====================================================
echo.
echo  * 실행 조건: 매일 아침 08:00 자동 실행 (미세 지터 적용)
echo  * 좋아요 간격: 1초 ~ 30초 사이 랜덤 지연
echo  * 일일 한도: 1,450 ~ 1,500회 사이 매일 랜덤 자동 조절
echo  * 원격 확인 없이 PC를 켜두시면 스스로 알아서 작동합니다.
echo.
echo ====================================================
echo.

set PYTHON_CMD=python
if exist ".venv\Scripts\python.exe" set PYTHON_CMD=.venv\Scripts\python.exe
if exist "venv\Scripts\python.exe" set PYTHON_CMD=venv\Scripts\python.exe
set PYTHONIOENCODING=utf-8

%PYTHON_CMD% auto_agent.py %*

if errorlevel 1 (
    echo.
    echo [!] 에이전트 실행 중 오류가 발생했습니다.
    pause
)
