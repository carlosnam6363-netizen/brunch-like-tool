@echo off
chcp 65001 > nul
title 윈도우 자동 작업 스케줄러 등록 해제

echo ====================================================
echo  브런치 자동 에이전트 - 윈도우 스케줄러 해제
echo ====================================================
echo.

schtasks /delete /tn "BrunchAutoLikeAgent" /f

if %errorlevel% equ 0 (
    echo.
    echo [*] 스케줄러에서 'BrunchAutoLikeAgent' 등록이 정상적으로 제거되었습니다.
) else (
    echo.
    echo [!] 등록된 작업을 찾을 수 없거나 이미 삭제되었습니다.
)

echo.
pause
