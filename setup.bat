@echo off
chcp 65001 > nul
echo ==========================================================
echo  브런치 연재글 자동 좋아요 도구 환경 설정 (Setup)
echo ==========================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [오류] Python이 설치되어 있지 않거나 PATH에 등록되지 않았습니다.
    echo https://www.python.org 에서 Python 3.10 이상을 설치해주세요.
    pause
    exit /b 1
)

echo [1/3] 가상환경(.venv) 확인 및 생성...
if not exist ".venv" (
    python -m venv .venv
    echo 가상환경이 생성되었습니다.
)

echo [2/3] 필수 패키지 설치...
call .venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo ==========================================================
echo [3/3] 설정 완료!
echo  - 데스크톱 GUI 실행: run_gui.bat
echo  - 웹 대시보드 실행: run_web.bat
echo ==========================================================
pause
