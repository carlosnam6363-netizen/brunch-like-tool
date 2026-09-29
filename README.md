# Brunch Like Tool (브런치 연재글 자동 좋아요 도구)

> **"어디서든 브라우저로 접속해 사용하거나, GitHub에서 다운로드받아 로컬에서 즉시 실행하세요!"**

브런치스토리(Brunch Story) 플랫폼에서 사용자가 지정한 요일에 올라온 연재 글들을 **최신순**으로 정렬하여 **1분 간격**으로 순차적으로 '좋아요(라이킷)'를 눌러주는 올인원 자동화 솔루션입니다.

- **기본 대상 URL**: `https://brunch.co.kr/serial/list#tue#PUBLISH_TIME` (화요일 연재 최신순)
- **어디서나 접근 가능**: 웹 클라우드 배포(Streamlit Cloud/Docker), 윈도우 무설치 GUI, 크로스플랫폼(Mac/Linux/CLI) 모두 지원

---

## 🌟 핵심 특징

1. **🌐 어디서든 웹으로 사용 가능 (클라우드/모바일/태블릿 완벽 호환)**:
   - 브라우저 설치 없이 **순수 HTTP API 모드**를 지원합니다.
   - 쿠키(Cookie) 하나만 붙여넣으면 PC가 꺼져 있어도 서버나 웹에서 1분 간격 자동 좋아요가 완벽히 동작합니다.
2. **💻 GitHub 다운로드 후 1클릭 실행 (Windows / Mac / Linux)**:
   - `setup.bat` (윈도우) 또는 `setup.sh` (맥/리눅스) 실행 시 가상환경 및 의존성이 자동 구성됩니다.
   - 데스크톱 GUI(`run_gui.bat`), 웹 대시보드(`run_web.bat`), 터미널 CLI를 모두 제공합니다.
3. **⏱️ 정확한 1분(60초) 간격 & 실시간 카운트다운**:
   - 계정 제재 및 플랫폼 어뷰징을 방지하기 위해 1분 지연 대기를 정확히 지킵니다.
4. **🛡️ 스마트 스킵 (중복 및 좋아요 취소 방지)**:
   - 이미 내가 좋아요를 누른 글은 자동으로 감지하여 건너뛰므로 기존 좋아요가 취소되지 않습니다.
5. **🔑 편리한 인증 옵션**:
   - **쿠키 직접 입력**: 1초 복사 북마크릿 제공, 웹/클라우드 환경에 최적화
   - **로컬 브라우저 자동 로그인**: 최초 1회만 카카오 로그인하면 프로필 세션(`brunch_profile/`)이 영구 보존됨

---

## 🚀 사용 방법 1: 웹(Web)으로 사용하기

별도의 프로그램을 설치하지 않고 웹 브라우저에서 바로 사용하거나 무료 클라우드에 배포할 수 있습니다.

### 방법 A: Streamlit Community Cloud 무료 배포 (가장 추천)
1. 본 저장소를 본인의 GitHub 계정으로 Fork(또는 Push)합니다.
2. [share.streamlit.io](https://share.streamlit.io)에 접속하여 GitHub 계정으로 로그인합니다.
3. **[New app]** 클릭 후:
   - **Repository**: `본인계정/brunch-like-tool`
   - **Main file path**: `app.py`
4. **[Deploy!]** 버튼을 누르면 1~2분 만에 나만의 브런치 자동 좋아요 웹사이트가 생성됩니다!
5. 스마트폰, 태블릿, 회사 컴퓨터 어디서든 생성된 URL로 접속하여 쿠키를 입력하고 사용하시면 됩니다.

### 방법 B: Docker 컨테이너로 실행 (서버/NAS)
```bash
# Docker Compose로 원클릭 백그라운드 가동
docker compose up -d
```
- 브라우저에서 `http://서버IP:8501` 로 접속하여 사용합니다.

---

## 💻 사용 방법 2: GitHub에서 다운로드하여 로컬에서 사용하기

### 🪟 Windows 환경
1. **저장소 다운로드**:
   - GitHub 상단의 `Code` -> `Download ZIP` 압축 해제 또는 `git clone`:
     ```bash
     git clone https://github.com/carlosnam6363-netizen/brunch-like-tool.git
     cd brunch-like-tool
     ```
2. **원클릭 환경 구성**:
   - `setup.bat` 더블클릭 (가상환경 및 라이브러리 자동 설치)
3. **프로그램 실행 (원하는 형태 선택)**:
   - **데스크톱 GUI 창 실행**: `run_gui.bat` 더블클릭
   - **웹 대시보드 실행**: `run_web.bat` 더블클릭
   - **터미널 CLI 실행**:
     ```bash
     python cli.py --day tue --order PUBLISH_TIME --interval 60
     ```

### 🍎 macOS / 🐧 Linux 환경
```bash
git clone https://github.com/carlosnam6363-netizen/brunch-like-tool.git
cd brunch-like-tool
chmod +x setup.sh run_web.sh run_gui.sh
./setup.sh

# 실행
./run_web.sh     # 웹 대시보드
./run_gui.sh     # 데스크톱 GUI
```

---

## 🍪 1초 만에 브런치 쿠키(Cookie) 복사하는 방법

웹/클라우드 환경에서 사용하실 때 쿠키를 복사하는 가장 간단한 방법입니다.

### 🌟 북마크릿 (Bookmarklet) 사용 (강력 추천)
1. 브라우저 북마크(즐겨찾기)를 하나 생성하고, URL(주소) 란에 아래 코드를 그대로 붙여넣습니다:
   ```javascript
   javascript:(function(){navigator.clipboard.writeText(document.cookie);alert('✅ 브런치 쿠키가 클립보드에 복사되었습니다!\n\n웹 대시보드의 쿠키 입력창에 [Ctrl + V] 로 붙여넣으세요.');})();
   ```
2. [brunch.co.kr](https://brunch.co.kr)에 접속하여 로그인합니다.
3. 북마크를 클릭하면 쿠키가 클립보드에 자동 복사됩니다!
4. 웹 대시보드의 `브런치 쿠키(Cookie) 붙여넣기` 란에 `Ctrl + V`로 붙여넣고 **[🔍 세션 검증]**을 누르면 끝!

---

## 📁 프로젝트 파일 구성

```
brunch-like-tool/
├── brunch_api.py         # 브런치 공식 API 연동 (글 수집, 쿠키 세션 검증, 순수 HTTP 라이킷)
├── browser_bot.py        # Selenium 브라우저 자동화 봇 (Chrome/Edge 지원, 세션 영구 보존)
├── scheduler.py          # 1분 간격 순차 제어, 일시정지, 재개, 중단 스케줄러 (API/브라우저 듀얼 모드)
├── gui.py                # Tkinter 기반 데스크톱 GUI 프로그램
├── app.py                # Streamlit 기반 반응형 웹 대시보드
├── cli.py                # 명령줄(CLI) 인터페이스
├── Dockerfile            # 웹/클라우드 배포용 Docker 이미지 정의
├── docker-compose.yml    # Docker Compose 원클릭 실행 설정
├── bookmarklet.js        # 1초 쿠키 복사 북마크릿 소스코드
├── run_gui.bat           # [Windows] GUI 1클릭 실행기
├── run_web.bat           # [Windows] Web 1클릭 실행기
├── setup.bat             # [Windows] 자동 셋업 배치
├── run_gui.sh            # [Mac/Linux] GUI 실행 스크립트
├── run_web.sh            # [Mac/Linux] Web 실행 스크립트
├── setup.sh              # [Mac/Linux] 자동 셋업 스크립트
├── build_exe.bat         # [Windows] 무설치 .exe 단독 실행 파일 빌더
├── requirements.txt      # 파이썬 의존 라이브러리 목록
└── README.md             # 종합 사용 설명서
```

---

## ⚙️ 상세 실행 옵션 (CLI)

```bash
python cli.py [옵션]

옵션 안내:
  -d, --day          요일 선택 (mon, tue, wed, thu, fri, sat, sun, com / 기본: tue)
  -o, --order        정렬 기준 (PUBLISH_TIME, POPULARITY / 기본: PUBLISH_TIME)
  -i, --interval     대기 간격 (초 단위 / 기본: 60)
  -c, --cookie       브런치 쿠키 문자열 (헤드리스/순수 HTTP 모드)
  --cookie-file      쿠키 텍스트 파일 경로
  -b, --browser      브라우저 선택 (chrome, edge / 기본: chrome)
  -m, --max-count    최대 처리할 글 수 (미지정 시 전체)
  --login            로그인 브라우저를 먼저 실행하여 세션 저장
```

---

## 🔒 보안 및 개인정보

- 사용자의 카카오 아이디/비밀번호를 프로그램이 직접 수집하거나 외부에 전송하지 않습니다.
- 쿠키 및 세션 정보는 사용자의 브라우저 또는 로컬 프로필(`brunch_profile/`) 내에서만 안전하게 보관됩니다.
