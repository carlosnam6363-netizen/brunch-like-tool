# Brunch Like Tool (브런치 연재글 자동 좋아요 도구)

> **"GitHub 웹사이트 자체에서 버튼 클릭 한 번으로 실행하거나, 매주 정해진 시간에 자동 스케줄로 실행하세요! (PC를 켜둘 필요가 없습니다)"**

브런치스토리(Brunch Story) 플랫폼에서 사용자가 지정한 요일에 올라온 연재 글들을 **최신순**으로 정렬하여 **1분 간격**으로 순차적으로 '좋아요(라이킷)'를 눌러주는 올인원 자동화 도구입니다.

- **목표 대상 URL**: `https://brunch.co.kr/serial/list#tue#PUBLISH_TIME` (화요일 연재 최신순)
- **어디서나 실행 가능**: **GitHub Actions(깃허브 자체 실행)**, **GitHub Codespaces**, **웹 클라우드 대시보드**, **로컬 PC(GUI/CLI)** 모두 지원

---

## ⚡ 1. 깃허브(GitHub) 자체에서 바로 사용하는 방법 (가장 추천!)

컴퓨터에 아무것도 설치할 필요 없이, **GitHub 웹사이트나 깃허브 모바일 앱**에서 직접 실행할 수 있습니다. PC를 꺼두어도 깃허브 클라우드 서버가 알아서 실행합니다.

### 1단계: 브런치 쿠키를 GitHub Secret에 1회 등록
1. 브런치 사이트에서 본인의 로그인 쿠키를 복사합니다.  
   *(가장 쉬운 방법: 본 저장소의 `bookmarklet.js` 북마크릿을 클릭하거나, 브런치에서 F12 콘솔에 `copy(document.cookie)` 입력)*
2. 본 GitHub 저장소 상단 메뉴의 **`Settings`** (설정) 클릭
3. 좌측 사이드바에서 **`Secrets and variables`** ➡️ **`Actions`** 클릭
4. **`New repository secret`** 버튼 클릭:
   - **Name**: `BRUNCH_COOKIE`
   - **Secret**: 복사한 브런치 쿠키 문자열 붙여넣기
5. **`Add secret`** 클릭하여 저장!

---

### 2단계: 깃허브에서 버튼 눌러 즉시 실행 (수동 실행)
1. 저장소 상단 메뉴의 **`Actions`** 탭을 클릭합니다.
2. 좌측 목록에서 **`Brunch Auto Like (브런치 연재글 자동 좋아요)`** 를 클릭합니다.
3. 우측의 **`Run workflow`** 드롭다운 버튼을 클릭합니다:
   - **연재 요일**: `tue` (화요일, 기본값)
   - **정렬 기준**: `PUBLISH_TIME` (최신순, 기본값)
   - **좋아요 간격**: `60` (초 단위 = 1분)
   - **최대 처리 글 수**: `0` (0이면 해당 요일 전체 글 처리)
4. 녹색 **`Run workflow`** 버튼을 누르면 깃허브 서버가 즉시 1분 간격으로 좋아요를 누르기 시작합니다!
5. 실행이 끝나면 Actions 상세 페이지에 **어떤 글들에 좋아요가 성공했는지 예쁜 마크다운 표 리포트**가 자동으로 기록됩니다.

---

### 3단계: 정기 자동 스케줄 실행 (크론 지원)
- 저장소의 [`.github/workflows/brunch_like.yml`](.github/workflows/brunch_like.yml) 파일에 기본적으로 **매주 화요일 오전 09:00 (한국 시간)** 자동 실행 스케줄(`cron: '0 0 * * 2'`)이 내장되어 있습니다.
- 쿠키만 Secret에 넣어두시면 매주 화요일 아침마다 컴퓨터를 켜지 않아도 알아서 최신 화요 연재글에 1분 간격으로 좋아요를 눌러줍니다!

---

## ☁️ 2. GitHub Codespaces로 브라우저 안에서 실행하기

1. 본 저장소 상단의 초록색 **`Code`** 버튼 클릭 ➡️ **`Codespaces`** 탭 선택
2. **`Create codespace on main`** 클릭
3. 웹 브라우저 안에서 클라우드 VS Code가 30초 만에 열리며 환경 설정이 자동으로 완료됩니다.
4. 터미널에서 다음 명령어를 입력하여 웹 대시보드나 CLI를 바로 사용할 수 있습니다:
   ```bash
   streamlit run app.py
   ```
   *(포트 8501이 자동 포워딩되어 새 브라우저 창에서 웹 대시보드가 열립니다)*

---

## 🌐 3. Streamlit Cloud 또는 개인 서버(Docker)로 웹 배포

- **Streamlit Community Cloud (무료 호스팅)**:
  1. [share.streamlit.io](https://share.streamlit.io)에 접속하여 GitHub 로그인
  2. `New app` ➡️ 본 저장소 선택 ➡️ Main file path: `app.py` ➡️ `Deploy!`
  3. 스마트폰이나 외부 PC에서 생성된 URL로 언제든지 접속하여 사용!
- **Docker 컨테이너 (개인 서버 / NAS)**:
  ```bash
  docker compose up -d
  ```

---

## 💻 4. GitHub에서 다운로드하여 내 컴퓨터(로컬)에서 실행하기

### 🪟 Windows 환경
1. 저장소를 다운로드(ZIP 압축 해제)하거나 `git clone`:
   ```bash
   git clone https://github.com/carlosnam6363-netizen/brunch-like-tool.git
   cd brunch-like-tool
   ```
2. **`setup.bat`** 더블클릭 (가상환경 및 필수 패키지 원클릭 자동 설치)
3. 원하는 방식으로 실행:
   - **데스크톱 GUI 창**: `run_gui.bat` 더블클릭
   - **웹 대시보드**: `run_web.bat` 더블클릭
   - **터미널 CLI**: `python cli.py --day tue --order PUBLISH_TIME --interval 60`
   - **무설치 .exe 빌드**: `build_exe.bat` 실행 시 `dist/BrunchLikeTool.exe` 생성

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

### 🌟 북마크릿 (Bookmarklet)
1. 브라우저 북마크(즐겨찾기)를 추가하고, 주소(URL) 란에 아래 코드를 등록합니다:
   ```javascript
   javascript:(function(){navigator.clipboard.writeText(document.cookie);alert('✅ 브런치 쿠키가 클립보드에 복사되었습니다!\n\nGitHub Secrets 또는 웹 대시보드에 붙여넣으세요.');})();
   ```
2. [brunch.co.kr](https://brunch.co.kr)에 로그인한 뒤 북마크를 누르면 쿠키가 복사됩니다!

---

## 📁 전체 프로젝트 구조

```
brunch-like-tool/
├── .github/
│   └── workflows/
│       └── brunch_like.yml     # ⚡ [GitHub Actions] 깃허브 웹에서 원클릭/스케줄 자동 실행
├── .devcontainer/
│   └── devcontainer.json       # ☁️ [GitHub Codespaces] 브라우저 클라우드 개발환경
├── .streamlit/
│   └── config.toml             # 웹 대시보드 테마 및 서버 설정
├── brunch_api.py               # 브런치 공식 API 연동 (글 수집, CSRF 토큰, 직접 라이킷)
├── browser_bot.py              # 셀레니움 브라우저 봇 (Chrome/Edge 지원, 세션 영구 보존)
├── scheduler.py                # 1분 간격 스케줄러 (GitHub Actions / 브라우저 듀얼 모드)
├── gui.py                      # 데스크톱 GUI 애플리케이션
├── app.py                      # 반응형 Streamlit 웹 대시보드
├── cli.py                      # GitHub Actions & 터미널용 CLI 스크립트
├── Dockerfile                  # Docker 웹 배포 정의
├── docker-compose.yml          # Docker Compose 원클릭 실행
├── bookmarklet.js              # 1초 쿠키 복사용 북마크릿
├── run_gui.bat / run_gui.sh    # 데스크톱 GUI 실행기
├── run_web.bat / run_web.sh    # 웹 대시보드 실행기
├── setup.bat / setup.sh        # 원클릭 환경설정 스크립트
├── build_exe.bat               # Windows 무설치 단독 실행 파일(.exe) 빌더
├── requirements.txt            # 파이썬 의존 패키지 목록
└── README.md                   # 종합 사용 설명서
```

---

## 🔒 보안 및 개인정보

- GitHub Actions 사용 시 `BRUNCH_COOKIE`는 GitHub의 암호화된 Secret 보관소에 저장되므로, 저장소가 공개(Public) 상태여도 외부에 전혀 노출되지 않습니다.
- 본 도구는 공식 API 목록 조회와 순수 HTTP 호출을 결합하여 가볍고 안전하게 동작합니다.
