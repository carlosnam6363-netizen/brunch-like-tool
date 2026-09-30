# Brunch Like Tool (브런치 연재글 자동 좋아요 도구)

[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-Live%20Website-00c6be?style=flat&logo=github)](https://carlosnam6363-netizen.github.io/brunch-like-tool/)
[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/deploy?repository=carlosnam6363-netizen/brunch-like-tool&branch=main&mainModule=app.py)
[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Auto%20Like-blue?logo=githubactions)](https://github.com/carlosnam6363-netizen/brunch-like-tool/actions/workflows/brunch_like.yml)

> **"웹 브라우저에서 직관적으로 1초~30초 랜덤 간격으로 우측 상단 하트를 자동 클릭하세요!"**
> 스마트폰, 태블릿, 다른 PC 어디서든 브라우저 주소창에 치기만 하면 접속할 수 있는 웹사이트입니다.

### 🌐 즉시 접속 가능한 웹사이트 주소:
1. **📱 GitHub Pages 공식 웹 포털 (실시간 활성화)**: [https://carlosnam6363-netizen.github.io/brunch-like-tool/](https://carlosnam6363-netizen.github.io/brunch-like-tool/)
2. **☁️ Streamlit Cloud 웹앱**: [https://share.streamlit.io/deploy?repository=carlosnam6363-netizen/brunch-like-tool&branch=main&mainModule=app.py](https://share.streamlit.io/deploy?repository=carlosnam6363-netizen/brunch-like-tool&branch=main&mainModule=app.py)

---

## 🌐 1. 웹사이트(웹 브라우저)에서 직관적으로 직접 실행하기 (가장 추천!)

웹 브라우저 화면에서 직관적인 3단계 안내를 보며 버튼 클릭으로 직접 조작할 수 있습니다.

### 접속 주소: `http://localhost:8501`
*(이미 웹 서버가 가동 중이므로 브라우저에서 바로 접속하시면 됩니다. 나중에 다시 켤 때는 `run_web.bat` 더블클릭)*

### 📱 직관적인 3단계 사용 흐름:
1. **[1단계] 로그인 및 인증**:
   - **쿠키 직접 입력**: 브런치 쿠키를 입력하고 `[🔍 세션 확인]` 클릭
   - 또는 **로컬 브라우저 자동 로그인**: `[🔑 카카오 로그인 브라우저 열기]`를 눌러 1회 로그인 (세션 영구 보존)
2. **[2단계] 요일 및 랜덤 간격 설정**:
   - 연재 요일: **화요일(tue)** 기본 선택 (월~일, 완결작 변경 가능)
   - 정렬: **최신순(PUBLISH_TIME)** 기본 선택
   - 대기 간격: **🎲 1초 ~ 30초 사이 랜덤 슬라이더** (원하는 범위로 자유 조절)
   - **`[📋 1. 연재 글 목록 불러오기]`** 클릭 ➡️ 해당 요일의 모든 연재 글이 테이블로 즉시 표시됨
3. **[3단계] 자동 좋아요 실행**:
   - **`[🚀 2. 랜덤 간격 자동 좋아요 시작]`** 클릭!
   - 실시간 메트릭(총 글 수, 성공, 스킵, 실패)과 함께 다음 글까지 **1~30초 랜덤 카운트다운 게이지**가 실시간으로 움직이며, 각 글의 **우측 상단 하트 버튼**을 자동으로 클릭합니다.

---

## ⚡ 2. GitHub Actions로 웹에서 실행하기 (무설치, PC 안 켜도 됨)

GitHub 웹사이트([github.com](https://github.com)) 안에서 버튼 하나로 실행하거나 매주 정기 스케줄로 자동 실행할 수 있습니다.

### 1단계: 브런치 쿠키를 GitHub Secret에 1회 등록
1. 브런치 사이트([brunch.co.kr](https://brunch.co.kr))에 로그인한 상태에서 콘솔(`F12` ➡️ Console)에 `copy(document.cookie)` 입력 후 엔터 쳐서 쿠키 복사
2. 저장소의 **`Settings`** ➡️ **`Secrets and variables`** ➡️ **`Actions`** ➡️ **`New repository secret`**
   - **Name**: `BRUNCH_COOKIE`
   - **Secret**: 복사한 쿠키 붙여넣기 ➡️ `Add secret`

### 2단계: 깃허브 웹에서 원클릭 실행
1. 저장소 상단의 **`Actions`** 탭 ➡️ **`Brunch Auto Like`** 클릭
2. 우측의 **`Run workflow`** 드롭다운 클릭:
   - 최소 대기: `1`초
   - 최대 대기: `30`초 (1초~30초 사이 랜덤 실행)
3. **`Run workflow`** 버튼 클릭 ➡️ 깃허브 클라우드가 백그라운드에서 1~30초 랜덤 간격으로 좋아요 처리 후 마크다운 리포트 기록!

---

## 💻 3. 데스크톱 GUI 및 CLI 실행

- **데스크톱 GUI 창 실행**: `run_gui.bat` 더블클릭 (1초~30초 랜덤 간격 스핀박스 제공)
- **터미널 CLI 실행**:
  ```bash
  python cli.py --day tue --order PUBLISH_TIME --min-interval 1 --max-interval 30
  ```

---

## 📱 4. 언제, 어디서든 스마트폰 / 다른 PC에서 웹사이트로 접속하기

스마트폰(아이폰, 갤럭시) 및 외부 노트북/PC에서 웹 브라우저로 접속하는 3가지 방법입니다.

### 🌟 [방법 A] 원클릭 외부 접속기 (즉시 접속)
1. `run_remote_web.bat` 더블클릭 실행
2. 화면에 표시되는 **`https://xxxxx.trycloudflare.com`** 보안 주소를 스마트폰 브라우저에 입력!
3. 포트포워딩이나 복잡한 설정 없이 LTE/5G 모바일 환경 및 외부 PC에서 즉시 접속 가능합니다.

### ☁️ [방법 B] Streamlit Community Cloud (평생 무료, 24시간 가동, PC 꺼져도 됨!)
GitHub 저장소와 연동하여 24시간 언제든 열려있는 영구 웹사이트로 만드는 방법:
1. **[share.streamlit.io](https://share.streamlit.io)** 접속 후 GitHub 계정으로 로그인
2. **`Create app`** ➡️ **`carlosnam6363-netizen/brunch-like-tool`** 저장소 선택
3. Main file path: `app.py` 확인 후 **`Deploy!`** 클릭
4. 약 1분 후 **`https://[원하는이름].streamlit.app`** 영구 도메인이 생성되어 스마트폰 홈 화면에 추가해두고 언제든 사용 가능!

### 🏠 [방법 C] 동일 Wi-Fi(공유기) 내 로컬 접속
1. 현재 PC에서 웹서버 실행 (`run_web.bat`)
2. 같은 Wi-Fi에 연결된 스마트폰/노트북에서 브라우저를 열고 `http://[현재PC의_IP]:8501` 접속

---

## 📁 전체 프로젝트 구조

```
brunch-like-tool/
├── app.py                      # 💖 [웹 대시보드] 직관적인 3단계 UI & 1~30초 랜덤 지연 실시간 모니터링
├── browser_bot.py              # 🎯 [브라우저 봇] 우측 상단 GNB 하트 버튼 정밀 타겟팅 및 클릭
├── scheduler.py                # 🎲 [스케줄러] 1초~30초 랜덤 대기 및 스킵/일시정지 제어
├── brunch_api.py               # 🌐 [브런치 API] 연재글 목록 수집, CSRF 토큰 추출, 직접 라이킷
├── gui.py                      # 🪟 [데스크톱 GUI] 윈도우 창 인터페이스 (랜덤 간격 지원)
├── cli.py                      # ⚡ [CLI/GitHub] GitHub Actions 및 터미널 실행기
├── .github/workflows/          # ☁️ [GitHub Actions] 1~30초 랜덤 좋아요 워크플로우
├── bookmarklet.js              # 🍪 1초 쿠키 복사 북마크릿
├── run_web.bat                 # 🌐 로컬 웹 대시보드 실행기
├── run_remote_web.bat          # 📱 스마트폰/외부 원격 접속 웹 실행기
├── run_gui.bat                 # 🪟 GUI 1클릭 실행기
└── requirements.txt            # 필요 패키지 목록
```
