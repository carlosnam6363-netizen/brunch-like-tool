"""
Brunch Like Tool - Streamlit Web Dashboard
브런치 연재글 웹 대시보드 및 자동 좋아요 제어기
- 웹 브라우저(PC, 모바일, 태블릿) 어디서든 접속하여 사용 가능
- 쿠키 기반 순수 HTTP API 모드 (클라우드/헤드리스 환경 100% 호환)
- 로컬 브라우저 자동화 모드 (Selenium Chrome/Edge) 지원
실행: streamlit run app.py
"""

import os
import sys
import time
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from brunch_api import fetch_serial_articles, check_user_session, parse_cookie_string, like_article_api
from browser_bot import BrunchBot

st.set_page_config(
    page_title="브런치 연재글 자동 좋아요 (Brunch Like Tool)",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("✨ 브런치 연재글 1분 간격 자동 좋아요 도구")
st.caption("목표 URL: `https://brunch.co.kr/serial/list#tue#PUBLISH_TIME` | 어디서든 웹 브라우저로 접속하여 간편하게 사용 가능")

# 세션 상태 초기화
if "articles" not in st.session_state:
    st.session_state.articles = []
if "cookie_str" not in st.session_state:
    st.session_state.cookie_str = ""
if "auth_user" not in st.session_state:
    st.session_state.auth_user = None
if "bot" not in st.session_state:
    st.session_state.bot = None
if "is_running" not in st.session_state:
    st.session_state.is_running = False

# 사이드바: 설정 및 인증
with st.sidebar:
    st.header("⚙️ 실행 설정")

    day_options = {
        "화요일 (tue - 기본)": "tue",
        "월요일 (mon)": "mon",
        "수요일 (wed)": "wed",
        "목요일 (thu)": "thu",
        "금요일 (fri)": "fri",
        "토요일 (sat)": "sat",
        "일요일 (sun)": "sun",
        "완결작 (com)": "com"
    }
    selected_day_label = st.selectbox("연재 요일 선택", list(day_options.keys()), index=0)
    day_code = day_options[selected_day_label]

    order_options = {
        "최신순 (PUBLISH_TIME - 기본)": "PUBLISH_TIME",
        "인기순 (POPULARITY)": "POPULARITY"
    }
    selected_order_label = st.selectbox("정렬 기준", list(order_options.keys()), index=0)
    order_code = order_options[selected_order_label]

    interval_sec = st.number_input(
        "좋아요 간격 (초)",
        min_value=5,
        max_value=300,
        value=60,
        step=5,
        help="어뷰징 방지 및 사이트 보호를 위해 기본 60초(1분) 간격으로 실행됩니다."
    )

    st.markdown("---")
    st.header("🔑 인증 방식 선택")

    auth_mode = st.radio(
        "사용할 인증 방식",
        ["🍪 쿠키(Cookie) 입력 (웹/클라우드 어디서든 권장)", "🖥️ 로컬 브라우저 자동 로그인 (PC 전용)"],
        index=0
    )

    if "쿠키" in auth_mode:
        cookie_input = st.text_area(
            "브런치 쿠키(Cookie) 붙여넣기",
            value=st.session_state.cookie_str,
            placeholder="b_uid=...; brunch_session=... 또는 전체 쿠키 문자열",
            height=100,
            help="브런치에 로그인된 브라우저의 쿠키를 붙여넣으시면 브라우저 창 없이 순수 HTTP로 초고속 실행됩니다."
        )
        st.session_state.cookie_str = cookie_input.strip()

        col_chk, col_clr = st.columns([2, 1])
        with col_chk:
            if st.button("🔍 세션 검증", use_container_width=True):
                if not st.session_state.cookie_str:
                    st.warning("쿠키를 먼저 입력해주세요.")
                else:
                    is_ok, user_or_err = check_user_session(st.session_state.cookie_str)
                    if is_ok:
                        st.session_state.auth_user = user_or_err
                        st.success(f"인증 성공! [{user_or_err}] 계정 확인됨")
                    else:
                        st.session_state.auth_user = None
                        st.error(f"인증 실패: {user_or_err}")
        with col_clr:
            if st.button("지우기", use_container_width=True):
                st.session_state.cookie_str = ""
                st.session_state.auth_user = None
                st.rerun()

        if st.session_state.auth_user:
            st.info(f"👤 현재 인증된 작가: **{st.session_state.auth_user}**")

        with st.expander("💡 1초 만에 쿠키 복사하는 방법"):
            st.markdown("""
            **방법 1: 북마크릿 (가장 추천)**
            1. 브라우저 북마크에 아래 코드를 URL로 저장합니다:
            ```javascript
            javascript:(function(){navigator.clipboard.writeText(document.cookie);alert('브런치 쿠키가 클립보드에 복사되었습니다!');})();
            ```
            2. [brunch.co.kr](https://brunch.co.kr)에 로그인한 뒤 북마크를 클릭하면 쿠키가 복사됩니다!

            **방법 2: 개발자 도구 (F12)**
            1. `brunch.co.kr`에서 `F12` 누름 -> `Console(콘솔)` 탭 클릭
            2. `copy(document.cookie)` 입력 후 엔터 치면 자동 복사됩니다.
            """)
    else:
        browser_type = st.selectbox("브라우저 선택", ["chrome", "edge"], index=0)
        if st.button("🔑 카카오 로그인 브라우저 열기", use_container_width=True):
            if not st.session_state.bot:
                st.session_state.bot = BrunchBot(browser_type=browser_type)
            st.session_state.bot.open_login_window()
            st.success("브라우저 창이 열렸습니다. 카카오 로그인을 진행해주세요 (세션 자동 저장).")

# 메인 화면 영역
col_action1, col_action2 = st.columns([1, 1])

with col_action1:
    if st.button("📋 1. 연재 글 목록 불러오기", use_container_width=True, type="secondary"):
        with st.spinner(f"'{selected_day_label}' 연재 글 목록을 브런치에서 가져오는 중..."):
            items = fetch_serial_articles(day=day_code, order=order_code)
            st.session_state.articles = items
            st.success(f"총 {len(items)}개의 연재 글을 성공적으로 가져왔습니다!")

with col_action2:
    start_btn = st.button("🚀 2. 자동 좋아요 시작 (1분 간격)", use_container_width=True, type="primary")

# 글 목록 테이블
if st.session_state.articles:
    st.markdown(f"### 📑 연재 글 목록 (총 {len(st.session_state.articles)}건)")
    df_data = []
    for idx, a in enumerate(st.session_state.articles):
        df_data.append({
            "#": idx + 1,
            "제목": a["article_title"],
            "부제": a["article_sub_title"],
            "작가": a["user_name"],
            "매거진": a["magazine_title"],
            "발행일시": a["publish_date_str"],
            "좋아요수": a["like_count"],
            "상태": a.get("status", "대기중"),
            "링크": a["url"]
        })
    df = pd.DataFrame(df_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

# 자동 좋아요 실행 로직
if start_btn:
    if not st.session_state.articles:
        st.warning("먼저 [1. 연재 글 목록 불러오기]를 눌러 글 목록을 조회해주세요.")
    else:
        # 인증 검증
        use_cookie = "쿠키" in auth_mode
        if use_cookie and not st.session_state.cookie_str:
            st.error("사이드바에서 브런치 쿠키를 입력해주세요! (클라우드/웹에서는 쿠키 입력이 필수입니다)")
            st.stop()

        articles = st.session_state.articles
        total = len(articles)

        progress_bar = st.progress(0)
        status_box = st.empty()
        countdown_box = st.empty()
        log_container = st.empty()

        logs = []
        success = 0
        skipped = 0
        failed = 0

        bot = None
        if not use_cookie:
            if not st.session_state.bot:
                st.session_state.bot = BrunchBot(browser_type=browser_type)
            bot = st.session_state.bot

        status_box.info(f"총 {total}개의 글에 대해 1분({interval_sec}초) 간격 좋아요 작업을 시작합니다...")

        for i, article in enumerate(articles):
            title = article["article_title"]
            author = article["user_name"]
            url = article["url"]
            user_id = article["user_id"]
            article_no = article["article_no"]

            status_box.markdown(f"**[{i + 1}/{total}] 진행 중:** `{title}` (작가: {author})")

            # 좋아요 수행
            if use_cookie:
                res_code, msg = like_article_api(user_id, article_no, st.session_state.cookie_str)
            else:
                res_code, msg = bot.like_article(url)

            now_str = time.strftime("%H:%M:%S")
            if res_code == "LIKED":
                success += 1
                article["status"] = "좋아요 완료"
                logs.append(f"[{now_str}] ✅ [성공] '{title}' 좋아요를 눌렀습니다.")
            elif res_code == "ALREADY_LIKED":
                skipped += 1
                article["status"] = "이미 좋아요됨"
                logs.append(f"[{now_str}] ℹ️ [스킵] '{title}' 이미 좋아요가 되어 있습니다.")
            elif res_code == "NOT_LOGGED_IN":
                failed += 1
                article["status"] = "로그인 필요"
                logs.append(f"[{now_str}] ❌ [오류] {msg}")
                st.error("로그인이 만료되었거나 올바르지 않습니다. 인증을 다시 진행해주세요.")
                break
            else:
                failed += 1
                article["status"] = "오류"
                logs.append(f"[{now_str}] ⚠️ [실패] '{title}': {msg}")

            progress_bar.progress((i + 1) / total)
            log_container.code("\n".join(reversed(logs[-12:])), language="text")

            # 1분 대기 (마지막 글 제외)
            if i < total - 1:
                for rem in range(interval_sec, 0, -1):
                    countdown_box.markdown(f"⏳ **다음 글 좋아요까지 남은 시간:** `{rem}초`")
                    time.sleep(1)
                countdown_box.empty()

        status_box.empty()
        st.balloons()
        st.success(f"🎉 모든 연재 글 처리가 완료되었습니다! (성공: {success}건, 스킵: {skipped}건, 실패: {failed}건)")
