@echo off
cd /d "%~dp0"
chcp 65001 > nul
title 윈도우 자동 작업 스케줄러 등록기

echo ====================================================
echo  브런치 자동 에이전트 - 윈도우 스케줄러 자동 등록
echo ====================================================
echo.
echo  PC가 켜져 있거나 켜지는 즉시, 매일 아침 08:00에
echo  사용자가 손대지 않아도 자동으로 백그라운드에서 실행되도록
echo  윈도우 작업 스케줄러에 등록합니다.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$action = New-ScheduledTaskAction -Execute '%~dp0run_auto_agent.bat' -Argument '--once' -WorkingDirectory '%~dp0';" ^
  "$trigger = New-ScheduledTaskTrigger -Daily -At 8:00AM;" ^
  "$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun -AllowStartIfOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 4);" ^
  "Register-ScheduledTask -TaskName 'BrunchAutoLikeAgent' -Action $action -Trigger $trigger -Settings $settings -Description '브런치 자동 좋아요 매일 아침 08:00 자동 실행 에이전트' -Force"

if %errorlevel% equ 0 (
    echo.
    echo [*] 윈도우 작업 스케줄러에 'BrunchAutoLikeAgent' 등록이 완료되었습니다!
    echo [*] 매일 아침 08:00에 자동 구동되며, 1~30초 랜덤 간격 및 일일 1,450~1,500회 좋아요를 완수합니다.
    echo [*] (만약 오전 8시에 PC가 꺼져 있었더라도, 이후 PC를 켜는 즉시 당일 작업을 자동 수행합니다.)
) else (
    echo.
    echo [!] 등록 실패. '관리자 권한으로 실행'을 확인해주세요.
)

echo.
pause
