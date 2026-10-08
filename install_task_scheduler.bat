@echo off
cd /d "%~dp0"
chcp 65001 > nul
title 윈도우 자동 작업 스케줄러 등록기

echo ====================================================
echo  브런치 자동 에이전트 - 윈도우 스케줄러 자동 등록
echo ====================================================
echo.
echo  PC가 켜져 있거나 켜지는 즉시, 매일 아침 06:00에
echo  사용자가 손대지 않아도 자동으로 백그라운드에서 실행되도록
echo  윈도우 작업 스케줄러에 등록합니다.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$action = New-ScheduledTaskAction -Execute '%~dp0run_auto_agent.bat' -Argument '--once' -WorkingDirectory '%~dp0';" ^
  "$t1 = New-ScheduledTaskTrigger -Daily -At 7:00AM;" ^
  "$t2 = New-ScheduledTaskTrigger -Daily -At 12:30PM;" ^
  "$t3 = New-ScheduledTaskTrigger -Daily -At 7:00PM;" ^
  "$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun -AllowStartIfOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2);" ^
  "Register-ScheduledTask -TaskName 'BrunchAutoLikeAgent' -Action $action -Trigger @($t1, $t2, $t3) -Settings $settings -Description '브런치 자동 좋아요 하루 3회(아침 07:00, 점심 12:30, 저녁 19:00) 배치 실행 에이전트' -Force"

if %errorlevel% equ 0 (
    echo.
    echo [*] 윈도우 작업 스케줄러에 'BrunchAutoLikeAgent' 등록이 완료되었습니다!
    echo [*] 하루 3회(아침 07:00, 점심 12:30, 저녁 19:00) 분할 실행되며,
    echo [*] 각 세션당 280~300개 무작위 수량으로 어제 요일 발행 글에 좋아요를 수행합니다.
    echo [*] (일일 총 한도: 1,400개, 세션 완료 시 브라우저 자동 종료)
) else (
    echo.
    echo [!] 등록 실패. '관리자 권한으로 실행'을 확인해주세요.
)

echo.
pause
