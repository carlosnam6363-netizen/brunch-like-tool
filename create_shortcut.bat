@echo off
cd /d "%~dp0"
chcp 65001 > nul
title 바탕화면 바로가기 생성
echo [*] 바탕화면에 '브런치 자동 좋아요 (GUI)' 바로가기를 생성/갱신합니다...
powershell -ExecutionPolicy Bypass -File "%~dp0create_shortcut.ps1"
echo.
pause
