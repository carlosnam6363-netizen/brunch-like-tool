@echo off
cd /d "%~dp0"
chcp 65001 > nul
title 브런치 카카오 로그인 도우미

set PYTHON_CMD=python
if exist ".venv\Scripts\python.exe" set PYTHON_CMD=.venv\Scripts\python.exe
if exist "venv\Scripts\python.exe" set PYTHON_CMD=venv\Scripts\python.exe
set PYTHONIOENCODING=utf-8

%PYTHON_CMD% login_helper.py
