@echo off
chcp 65001 > nul
echo ====================================================
echo  브런치 특정 요일 연재글 자동 좋아요 웹 대시보드
echo ====================================================
echo.

if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -m streamlit run app.py
) else (
    python -m streamlit run app.py
)

if %errorlevel% neq 0 (
    echo.
    echo [안내] 실행 중 오류가 발생했습니다. 먼저 setup.bat을 실행해보세요.
)
pause
