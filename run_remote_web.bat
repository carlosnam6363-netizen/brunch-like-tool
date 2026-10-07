@echo off
cd /d "%~dp0"
chcp 65001 > nul
title 브런치 자동 좋아요 - 원격 모바일 웹 실행기

echo ====================================================
echo  브런치 자동 좋아요 - 원격 모바일 웹 접속기
echo  [스마트폰/태블릿 어디서든 브라우저로 접속 가능]
echo ====================================================
echo.

set PYTHON_CMD=python
if exist ".venv\Scripts\python.exe" set PYTHON_CMD=.venv\Scripts\python.exe
if exist "venv\Scripts\python.exe" set PYTHON_CMD=venv\Scripts\python.exe

if not exist "cloudflared.exe" (
    echo [*] 원격 접속 도구 cloudflared 다운로드 중...
    curl -L -o cloudflared.exe "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
    if errorlevel 1 (
        echo [!] 다운로드 실패. 인터넷 연결을 확인해주세요.
        pause
        exit /b 1
    )
)

echo [*] Streamlit 웹 서버 확인 및 실행 중...
start /B "" %PYTHON_CMD% -m streamlit run app.py --server.headless true --server.port 8501 > nul 2>&1
ping -n 3 127.0.0.1 > nul

echo.
echo ====================================================
echo  스마트폰 접속용 보안 웹 주소를 생성하고 연결합니다.
echo  잠시 후 아래 박스 안에 https://...trycloudflare.com 주소가 표시됩니다.
echo  해당 주소를 스마트폰 브라우저에 입력하여 접속하세요.
echo  [안내] 이 창을 켜두는 동안 원격 모바일 접속이 유지됩니다.
echo ====================================================
echo.

cloudflared.exe tunnel --url http://localhost:8501

echo.
echo 프로그램이 종료되었습니다.
pause
