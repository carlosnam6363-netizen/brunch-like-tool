@echo off
cd /d "%~dp0"
chcp 65001 > nul
title 브런치 쿠키 메모장 열기

if not exist "brunch_profile" mkdir "brunch_profile"
if not exist "brunch_profile\last_cookie.txt" type nul > "brunch_profile\last_cookie.txt"

echo [*] 메모장으로 쿠키 파일(last_cookie.txt)을 엽니다...
echo [*] 복사한 브런치 쿠키를 붙여넣고 [Ctrl + S]로 저장 후 메모장을 닫아주세요.
start notepad "brunch_profile\last_cookie.txt"
