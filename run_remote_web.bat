@echo off
chcp 65001 > nul
title 브런치 자동 좋아요 - 원격 웹 접속기 (모바일/타 PC 접속)

echo ================================================================
echo    💖 브런치 자동 좋아요 - 원격 웹 접속 실행기
echo    (스마트폰, 태블릿, 다른 PC 어디서든 브라우저로 접속 가능)
echo ================================================================
echo.

cd /d "%~dp0"

:: 1. 가상환경 또는 기본 파이썬 설정
set PYTHON_CMD=python
if exist "venv\Scripts\python.exe" (
    set PYTHON_CMD=venv\Scripts\python.exe
)

:: 2. cloudflared.exe 다운로드 확인
if not exist "cloudflared.exe" (
    echo [*] 원격 외부 접속용 터널 도구(cloudflared)를 다운로드합니다...
    curl -L -o cloudflared.exe "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
    if errorlevel 1 (
        echo [!] 다운로드 실패. 인터넷 연결을 확인해주세요.
        pause
        exit /b 1
    )
    echo [*] 다운로드 완료!
)

:: 3. 로컬 Streamlit 웹 서버 백그라운드 시작 (이미 켜져있지 않다면)
echo [*] Streamlit 웹 서버 확인 및 실행 중...
start /B "" %PYTHON_CMD% -m streamlit run app.py --server.headless true --server.port 8501 > nul 2>&1
timeout /t 2 /nobreak > nul

:: 4. Cloudflare Tunnel 실행 (스마트폰/외부 접속용 HTTPS 주소 발급)
echo.
echo ================================================================
echo  🌐 스마트폰 / 다른 PC 접속용 인터넷 주소(HTTPS)를 연결합니다...
echo  잠시 후 하단에 생성되는 [https://xxxxx.trycloudflare.com] 주소를
echo  스마트폰이나 다른 컴퓨터 브라우저에 입력하여 접속하세요!
echo ================================================================
echo.

.\cloudflared.exe tunnel --url http://localhost:8501
pause
