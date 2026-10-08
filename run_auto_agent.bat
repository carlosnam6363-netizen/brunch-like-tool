@echo off
cd /d "%~dp0"
chcp 65001 > nul
title 브런치 자동 좋아요 - 하루 3회 분할 자동 실행 에이전트

echo ====================================================
echo  브런치 자동 좋아요 - 3회 배치 분할 자율 에이전트
echo ====================================================
echo.
echo  * 대상: 어제 요일 발행 연재 글 목록
echo  * 분할 실행: 아침(07:00경), 점심(12:30경), 저녁(19:00경)
echo  * 세션당 한도: 280 ~ 300개 무작위 제한 (일일 총 1,400개)
echo  * 이상행동 방지: 가우시안 딜레이, 세션 간 브라우저 완전 종료
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
