@echo off
cd /d "%~dp0"
chcp 65001 > nul
title 브런치 자동 좋아요 에이전트 (수동 실행)

echo ====================================================
echo  브런치 자동 좋아요 에이전트 (즉시 1회 실행)
echo ====================================================
echo.
echo  * 대상: 어제 요일 발행 연재 글 목록
echo  * 실행 방식: 시간대별 예약 없이 실행 시 즉시 동작
echo  * 일일 한도: 1,400개 (가우시안 딜레이 적용)
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
