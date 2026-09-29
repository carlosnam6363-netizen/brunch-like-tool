"""
Brunch Like Tool - Streamlit Web Dashboard
브런치 연재글 웹 대시보드 및 자동 좋아요 제어기
실행: streamlit run app.py
"""

import os
import sys
import time
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from brunch_api import fetch_serial_articles
from browser_bot import BrunchBot
from scheduler import LikeScheduler

st.set_page_config(
    page_title="브런치 연재글 자동 좋아요 도구",
    page_icon="✨",
    layout="wide"
)

st.title("✨ 브런치 연재글 1분 간격 자동 좋아요 도구")
st.markdown("목표 URL: `https://brunch.co.kr/serial/list#tue#PUBLISH_TIME` (설정한 요일의 최신 연재 글을 순차적으로 1분 간격 좋아요)")

# 세션 상태 초기화
if "articles" not in st.session_state:
    st.session_state.articles = []
if "logs" not in st.session_state:
    st.session_state.logs = []
if "bot" not in st.session_state:
    st.session_state.bot = None

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 실행 설정")

    day_options = {
        "화요일 (tue)": "tue",
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
        "최신순 (PUBLISH_TIME)": "PUBLISH_TIME",
        "인기순 (POPULARITY)": "POPULARITY"
    }
    selected_order_label = st.selectbox("정렬 기준", list(order_options.keys()), index=0)
    order_code = order_options[selected_order_label]

    interval_sec = st.number_input("좋아요 간격 (초)", min_value=10, max_value=300, value=60, step=5)
    browser_type = st.selectbox("브라우저 선택", ["chrome", "edge"], index=0)

    st.markdown("---")
    st.subheader("🔑 계정 로그인")
    st.info("카카오 계정으로 1회 로그인하면 세션이 영구 보존됩니다.")

    if st.button("카카오 로그인 창 열기"):
        if not st.session_state.bot:
            st.session_state.bot = BrunchBot(browser_type=browser_type)
        st.session_state.bot.open_login_window()
        st.success("브라우저가 열렸습니다. 카카오 로그인을 완료해주세요!")

# 메인 화면
col1, col2 = st.columns([1, 1])

with col1:
    if st.button("📋 1. 연재 글 목록 불러오기", use_container_width=True, type="secondary"):
        with st.spinner(f"'{selected_day_label}' 연재 글 목록을 브런치에서 가져오는 중..."):
            articles = fetch_serial_articles(day=day_code, order=order_code)
            st.session_state.articles = articles
            st.success(f"총 {len(articles)}개의 연재 글을 성공적으로 가져왔습니다!")

with col2:
    start_btn = st.button("🚀 2. 자동 좋아요 시작 (1분 간격)", use_container_width=True, type="primary")

# 글 목록 표시
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
            "현재 좋아요": a["like_count"],
            "상태": a.get("status", "대기중"),
            "URL": a["url"]
        })
    df = pd.DataFrame(df_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

# 실행 처리
if start_btn:
    if not st.session_state.articles:
        st.warning("먼저 [연재 글 목록 불러오기]를 눌러 글 목록을 조회해주세요.")
    else:
        if not st.session_state.bot:
            st.session_state.bot = BrunchBot(browser_type=browser_type)

        bot = st.session_state.bot
        articles = st.session_state.articles
        total = len(articles)

        progress_bar = st.progress(0)
        status_text = st.empty()
        countdown_text = st.empty()
        log_box = st.empty()

        logs = []
        success = 0
        skipped = 0
        failed = 0

        for i, article in enumerate(articles):
            title = article["article_title"]
            author = article["user_name"]
            url = article["url"]

            status_text.markdown(f"**[{i + 1}/{total}] 진행 중:** `{title}` ({author})")
            res_code, msg = bot.like_article(url)

            now_str = time.strftime("%H:%M:%S")
            if res_code == "LIKED":
                success += 1
                article["status"] = "좋아요 완료"
                logs.append(f"[{now_str}] ✅ [성공] '{title}' 좋아요 완료")
            elif res_code == "ALREADY_LIKED":
                skipped += 1
                article["status"] = "이미 좋아요됨"
                logs.append(f"[{now_str}] ℹ️ [스킵] '{title}' 이미 좋아요된 상태")
            elif res_code == "NOT_LOGGED_IN":
                failed += 1
                article["status"] = "로그인 필요"
                logs.append(f"[{now_str}] ❌ [오류] 로그인이 필요합니다. 작업을 중단합니다.")
                st.error("로그인이 되어있지 않습니다. 사이드바에서 [카카오 로그인 창 열기]를 눌러 로그인해주세요.")
                break
            else:
                failed += 1
                article["status"] = "오류"
                logs.append(f"[{now_str}] ⚠️ [실패] '{title}': {msg}")

            progress_bar.progress((i + 1) / total)
            log_box.code("\n".join(reversed(logs[-10:])), language="text")

            # 1분 대기
            if i < total - 1:
                for rem in range(interval_sec, 0, -1):
                    countdown_text.markdown(f"⏳ **다음 글까지 대기 중:** `{rem}초`")
                    time.sleep(1)
                countdown_text.empty()

        st.success(f"🎉 모든 작업이 완료되었습니다! (성공: {success}건, 스킵: {skipped}건, 실패: {failed}건)")
