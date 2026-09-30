@echo off
cd /d "%~dp0"
chcp 65001 > nul
title 브런치 자동 좋아요 (웹 대시보드)

echo ====================================================
echo  브런치 연재글 자동 좋아요 도구 (웹 대시보드)
echo ====================================================
echo.

set PYTHON_CMD=python
if exist ".venv\Scripts\python.exe" set PYTHON_CMD=.venv\Scripts\python.exe
if exist "venv\Scripts\python.exe" set PYTHON_CMD=venv\Scripts\python.exe

echo [*] 웹 대시보드를 시작합니다 (http://localhost:8501)...
%PYTHON_CMD% -m streamlit run app.py
pause
