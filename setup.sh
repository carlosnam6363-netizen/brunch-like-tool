#!/bin/bash
set -e

echo "=========================================================="
echo " 브런치 연재글 자동 좋아요 도구 환경 설정 (macOS / Linux)"
echo "=========================================================="
echo ""

if ! command -v python3 &> /dev/null; then
    echo "[오류] python3 명령어를 찾을 수 없습니다. Python 3.10 이상을 설치해주세요."
    exit 1
fi

echo "[1/2] 가상환경(.venv) 생성 중..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

source .venv/bin/activate

echo "[2/2] 필수 패키지 설치 중..."
pip install --upgrade pip
pip install -r requirements.txt

chmod +x run_web.sh 2>/dev/null || true
chmod +x run_gui.sh 2>/dev/null || true

echo ""
echo "=========================================================="
echo " 설정 완료!"
echo "  - 웹 대시보드 실행: ./run_web.sh"
echo "  - CLI 실행: source .venv/bin/activate && python cli.py"
echo "=========================================================="
