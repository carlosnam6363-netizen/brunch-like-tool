@echo off
chcp 65001 > nul
echo ==========================================================
echo  Brunch Like Tool - 무설치 단독 실행 파일 (.exe) 빌드
echo ==========================================================
echo.

pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo [1/2] PyInstaller 설치 중...
    pip install pyinstaller
)

echo [2/2] BrunchLikeTool.exe 단독 실행 파일 빌드 중...
pyinstaller --noconfirm --onedir --windowed --name "BrunchLikeTool" ^
    --add-data "brunch_api.py;." ^
    --add-data "browser_bot.py;." ^
    --add-data "scheduler.py;." ^
    gui.py

echo.
echo ==========================================================
echo 빌드가 완료되었습니다!
echo 생성 위치: dist\BrunchLikeTool\BrunchLikeTool.exe
echo ==========================================================
pause
