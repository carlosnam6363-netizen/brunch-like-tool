@echo off
cd /d "%~dp0"
chcp 65001 > nul
title 윈도우 자동 작업 스케줄러 등록기

echo ====================================================
echo  브런치 자동 에이전트 - 윈도우 스케줄러 자동 등록
echo ====================================================
echo.
echo  PC 부팅(로그인) 시 또는 매일 아침 06:00에
echo  사용자가 손대지 않아도 자동으로 백그라운드에서 실행되도록
echo  윈도우 작업 스케줄러에 등록합니다.
echo.

set SCRIPT_PATH=%~dp0run_auto_agent.bat

schtasks /create /tn "BrunchAutoLikeAgent" /tr "\"%SCRIPT_PATH%\"" /sc daily /st 06:00 /f

if %errorlevel% equ 0 (
    echo.
    echo [*] 윈도우 작업 스케줄러에 'BrunchAutoLikeAgent' 등록이 완료되었습니다!
    echo [*] 매일 아침 06:00에 자동 구동되며, 06~08시 사이 무작위 시각에 좋아요를 수행합니다.
) else (
    echo.
    echo [!] 등록 실패. '관리자 권한으로 실행'을 확인해주세요.
)

echo.
pause
