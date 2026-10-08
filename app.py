"""
Brunch Like Tool - Streamlit Web Dashboard
브런치 연재글 웹 대시보드 및 자동 좋아요 제어기
- 1초 ~ 30초 사이 랜덤 간격 좋아요 지원
- 직관적인 단계별 UI (로그인 -> 글 조회 -> 실시간 랜덤 좋아요)
- 브런치 우측 상단 하트 버튼 기준 클릭
- HTTP Keep-Alive 세션 재사용 및 성능 최적화
실행: streamlit run app.py
"""

import os
import sys
import time
import random
import requests
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from brunch_api import fetch_serial_articles, fetch_multiple_days_articles, check_user_session, parse_cookie_string, like_article_api, sort_days_canonically
from browser_bot import BrunchBot
from daily_stats import get_today_liked_count, record_daily_like, can_like_today, reset_today_liked_count, DAILY_LIKE_LIMIT, get_today_daily_limit

st.set_page_config(
    page_title="브런치 연재글 자동 좋아요 도구",
    page_icon="💖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# UI 커스텀 스타일링
st.markdown("""
<style>
    .main-header {
        font-size: 26px;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 2px;
    }
    .sub-header {
        font-size: 14px;
        color: #64748b;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">💖 브런치 연재글 자동 좋아요 도구</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">목표 URL: <code>https://brunch.co.kr/serial/list#tue#PUBLISH_TIME</code> '
    '| 1초~30초 랜덤 간격으로 각 글의 <b>우측 상단 하트 버튼</b>을 순차 클릭합니다.</div>',
    unsafe_allow_html=True
)

# 세션 상태 초기화 및 자동 로그인 복원
if "articles" not in st.session_state:
    st.session_state.articles = []
if "cookie_str" not in st.session_state:
    default_cookie = os.getenv("BRUNCH_COOKIE", "")
    if not default_cookie:
        try:
            if hasattr(st, "secrets") and "BRUNCH_COOKIE" in st.secrets:
                default_cookie = str(st.secrets["BRUNCH_COOKIE"])
        except Exception:
            pass
    cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brunch_profile", "last_cookie.txt")
    if not default_cookie and os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                default_cookie = f.read().strip()
        except Exception:
            pass
    st.session_state.cookie_str = default_cookie

if "auth_user" not in st.session_state:
    if st.session_state.cookie_str:
        is_ok, user_info = check_user_session(st.session_state.cookie_str)
        st.session_state.auth_user = user_info if is_ok else None
    else:
        st.session_state.auth_user = None

if "bot" not in st.session_state:
    st.session_state.bot = None
if "completed_keys" not in st.session_state:
    st.session_state.completed_keys = set()

# 사이드바: 북마크릿 및 동작 원리 안내
with st.sidebar:
    st.header("💡 간편 쿠키 복사 도구")
    st.markdown("""
    **1초 북마크릿 복사**
    브런치 사이트([brunch.co.kr](https://brunch.co.kr))에 로그인한 상태에서 아래 북마크릿을 클릭하면 쿠키가 클립보드에 자동 복사됩니다:
    """)
    st.code(
        "javascript:(function(){navigator.clipboard.writeText(document.cookie);alert('✅ 브런치 쿠키가 복사되었습니다!');})();",
        language="javascript"
    )
    st.caption("복사한 쿠키를 [인증 설정]의 쿠키 란에 붙여넣으시면 됩니다.")
    st.markdown("---")
    st.info("🎯 **우측 상단 하트 타겟팅**: 글 페이지 상단 GNB의 하트 아이콘을 정밀 감지하여 클릭하며, 이미 좋아요를 누른 글은 자동으로 안전하게 건너뜁니다.")

# ----------------------------------------------------
# 1단계: 인증 설정 (쿠키 / 브라우저)
# ----------------------------------------------------
st.markdown("### 🔑 [1단계] 로그인 및 인증")
tab_cookie, tab_browser = st.tabs(["🍪 쿠키(Cookie) 직접 입력 (웹/클라우드 어디서든 동작)", "🖥️ 로컬 브라우저 자동 로그인 (PC 전용)"])

with tab_cookie:
    col_c1, col_c2 = st.columns([3, 1])
    with col_c1:
        cookie_val = st.text_input(
            "브런치 로그인 쿠키 붙여넣기",
            value=st.session_state.cookie_str,
            type="password",
            placeholder="b_uid=...; brunch_session=... 또는 전체 쿠키 문자열",
            help="브런치에 로그인된 브라우저의 쿠키를 입력하세요."
        )
        if cookie_val != st.session_state.cookie_str:
            st.session_state.cookie_str = cookie_val.strip()

    with col_c2:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("🔍 세션 확인", key="btn_check_cookie"):
            if not st.session_state.cookie_str:
                st.warning("쿠키를 먼저 입력해주세요.")
            else:
                is_ok, user_info = check_user_session(st.session_state.cookie_str)
                if is_ok:
                    st.session_state.auth_user = user_info
                    try:
                        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                        with open(cache_path, "w", encoding="utf-8") as f:
                            f.write(st.session_state.cookie_str)
                    except Exception:
                        pass
                    st.success(f"인증 성공! [{user_info}] (세션 자동 기억됨)")
                else:
                    st.session_state.auth_user = None
                    st.error(f"세션 확인 실패: {user_info}")

    if st.session_state.auth_user:
        st.success(f"✅ 현재 로그인 작가: **{st.session_state.auth_user}** 계정으로 인증되었습니다.")

with tab_browser:
    col_b1, col_b2 = st.columns([2, 2])
    with col_b1:
        browser_choice = st.selectbox("사용할 브라우저", ["chrome", "edge"], index=0)
    with col_b2:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("🔑 카카오 로그인 브라우저 열기", key="btn_open_browser"):
            if not st.session_state.bot:
                st.session_state.bot = BrunchBot(browser_type=browser_choice)
            st.session_state.bot.open_login_window()
            st.info("브라우저 창이 열렸습니다. 카카오 계정으로 로그인을 완료해주세요 (세션 자동 저장).")

st.markdown("---")

# ----------------------------------------------------
# 2단계: 대상 글 및 랜덤 간격 설정
# ----------------------------------------------------
st.markdown("### ⚙️ [2단계] 요일 및 대기 간격 설정")

# 일일 누적 좋아요 현황 표시
cur_today_liked = get_today_liked_count()
cur_rem_liked = max(0, DAILY_LIKE_LIMIT - cur_today_liked)

col_s1, col_s2 = st.columns([3, 1])
with col_s1:
    if cur_rem_liked == 0:
        st.error(f"🛑 **오늘 일일 최대 좋아요 한도 도달:** `{cur_today_liked:,} / {DAILY_LIKE_LIMIT:,}회` (오늘 추가 작업 불가, 내일 리셋됩니다)")
    else:
        st.info(f"💖 **오늘 누적 좋아요 현황:** `{cur_today_liked:,} / {DAILY_LIKE_LIMIT:,}회` (오늘 잔여: **{cur_rem_liked:,}회** 가능)")
with col_s2:
    if st.button("↺ 오늘 카운트 초기화", key="btn_reset_daily"):
        reset_today_liked_count()
        st.rerun()

col_opt1, col_opt2, col_opt3 = st.columns([1.5, 1, 1.5])

with col_opt1:
    day_map = {
        "월요일 (mon)": "mon",
        "화요일 (tue)": "tue",
        "수요일 (wed)": "wed",
        "목요일 (thu)": "thu",
        "금요일 (fri)": "fri",
        "토요일 (sat)": "sat",
        "일요일 (sun)": "sun",
        "완결작 (com)": "com"
    }
    sel_day_labels = st.multiselect(
        "연재 요일 (다중 선택 가능)",
        options=list(day_map.keys()),
        default=["화요일 (tue)"],
        help="여러 요일을 선택하면 모든 해당 요일의 글 목록을 중복 없이 통합 수집합니다."
    )
    sel_day_codes = sort_days_canonically([day_map[lbl] for lbl in sel_day_labels])

with col_opt2:
    order_map = {
        "최신순 (PUBLISH_TIME)": "PUBLISH_TIME",
        "인기순 (POPULARITY)": "POPULARITY"
    }
    sel_order_label = st.selectbox("정렬 기준", list(order_map.keys()), index=0)
    order_code = order_map[sel_order_label]

with col_opt3:
    interval_range = st.slider(
        "🎲 좋아요 랜덤 대기 간격 (초)",
        min_value=1,
        max_value=60,
        value=(1, 30),
        step=1,
        help="각 글에 좋아요를 누르기 전, 설정한 최소~최대 초 사이에서 무작위로 시간을 선택해 대기합니다."
    )
    min_sec, max_sec = interval_range
    st.caption(f"⚡ 각 글 처리 시마다 **{min_sec}초 ~ {max_sec}초 사이의 랜덤한 시간** 동안 대기합니다.")

# 글 목록 조회 & 시작 버튼
col_btn1, col_btn2 = st.columns([1, 1])
with col_btn1:
    if st.button("📋 1. 연재 글 목록 불러오기", type="secondary"):
        if not sel_day_codes:
            st.warning("수집할 연재 요일을 최소 1개 이상 선택해주세요!")
        else:
            with st.spinner("선택한 요일 목록의 글을 월요일~완결 순서로 브런치에서 실시간 수집 중..."):
                items = fetch_multiple_days_articles(days=sel_day_codes, order=order_code)
                st.session_state.articles = items
                # 요일별 수집 건수 통계
                day_counts = {}
                for art in items:
                    dk = art.get("source_day_kor") or art.get("source_day", "-")
                    day_counts[dk] = day_counts.get(dk, 0) + 1
                breakdown = ", ".join([f"{k}: {c:,}건" for k, c in day_counts.items()])
                st.success(f"총 {len(items):,}개의 연재 글 목록을 월요일~완결 순서로 성공적으로 불러왔습니다! ({breakdown})")

with col_btn2:
    start_auto_like = st.button("🚀 2. 랜덤 간격 자동 좋아요 시작", type="primary")

# 글 목록 탭 분리 표시 (대기 중 vs 좋아요 완료)
pending_list = [a for a in st.session_state.articles if a["url"] not in st.session_state.completed_keys and a.get("status") not in ("좋아요 완료", "이미 좋아요됨")]
done_list = [a for a in st.session_state.articles if a["url"] in st.session_state.completed_keys or a.get("status") in ("좋아요 완료", "이미 좋아요됨")]

if st.session_state.articles:
    st.markdown(f"#### 📑 연재 글 목록 (대기 {len(pending_list):,}건 / 완료 {len(done_list):,}건)")
    tab_pend, tab_comp = st.tabs([f"📑 대기 중인 글 ({len(pending_list):,}건)", f"💖 좋아요 완료 ({len(done_list):,}건)"])
    
    with tab_pend:
        if pending_list:
            df_rows = [
                {
                    "#": idx + 1,
                    "요일": a.get("source_day_kor") or a.get("source_day", "-"),
                    "글 제목": a["article_title"],
                    "작가": a["user_name"],
                    "매거진": a["magazine_title"],
                    "발행일시": a["publish_date_str"],
                    "현재 좋아요": a["like_count"],
                    "상태": a.get("status", "대기중"),
                    "URL": a["url"]
                }
                for idx, a in enumerate(pending_list)
            ]
            st.dataframe(pd.DataFrame(df_rows), hide_index=True, use_container_width=True)
        else:
            st.info("대기 중인 글이 없습니다. 모든 글에 이미 좋아요가 완료되었습니다.")

    with tab_comp:
        if done_list:
            df_done = [
                {
                    "#": idx + 1,
                    "요일": a.get("source_day_kor") or a.get("source_day", "-"),
                    "글 제목": a["article_title"],
                    "작가": a["user_name"],
                    "매거진": a["magazine_title"],
                    "발행일시": a["publish_date_str"],
                    "처리 상태": a.get("status", "완료"),
                    "URL": a["url"]
                }
                for idx, a in enumerate(done_list)
            ]
            st.dataframe(pd.DataFrame(df_done), hide_index=True, use_container_width=True)
        else:
            st.caption("아직 완료된 글이 없습니다.")

# ----------------------------------------------------
# 3단계: 자동 좋아요 실시간 실행
# ----------------------------------------------------
if start_auto_like:
    today_limit = get_today_daily_limit()
    can_proceed, today_cnt, remaining = can_like_today(today_limit)
    if not can_proceed:
        st.warning(f"🛑 오늘 이미 일일 최대 좋아요 한도({today_limit:,}회 중 {today_cnt:,}회)를 모두 달성하였습니다. 카카오/브런치 계정 보호를 위해 내일 다시 실행해주세요.")
        st.stop()

    if not st.session_state.articles:
        st.warning("먼저 [1. 연재 글 목록 불러오기]를 눌러 글 목록을 조회해주세요.")
    else:
        # 중복 방지: 대기 중인 글만 대상으로 필터링
        articles = [a for a in st.session_state.articles if a["url"] not in st.session_state.completed_keys and a.get("status") not in ("좋아요 완료", "이미 좋아요됨")]
        if not articles:
            st.info("대기 중인 글이 없거나 모든 글의 좋아요가 이미 완료되었습니다!")
            st.stop()

        use_cookie = bool(st.session_state.cookie_str)
        if not use_cookie and not st.session_state.bot:
            st.session_state.bot = BrunchBot(browser_type="chrome")

        total = len(articles)

        st.markdown("---")
        st.markdown("### 📊 실시간 실행 현황")

        col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
        col_m1.metric("총 대상 글", f"{total}건")
        m_success = col_m2.metric("성공 💖", "0건")
        m_skip = col_m3.metric("스킵(이미 누름) ℹ️", "0건")
        m_fail = col_m4.metric("실패 ❌", "0건")
        m_daily = col_m5.metric("오늘 누적 좋아요", f"{today_cnt} / {today_limit}회")

        progress_bar = st.progress(0)
        current_status = st.empty()
        countdown_box = st.empty()
        countdown_gauge = st.empty()
        log_box = st.empty()

        logs = []
        success = 0
        skipped = 0
        failed = 0

        # HTTP 모드 시 단일 세션 재사용
        http_session = None
        if use_cookie:
            http_session = requests.Session()
            http_session.cookies.update(parse_cookie_string(st.session_state.cookie_str))

        try:
            for i, article in enumerate(articles):
                cur_cnt = get_today_liked_count()
                if cur_cnt >= today_limit:
                    logs.append(f"[{time.strftime('%H:%M:%S')}] 🛑 일일 최대 좋아요 한도({today_limit}회)에 도달하여 작업을 안전하게 자동 중단합니다.")
                    st.warning(f"일일 최대 한도({today_limit}회)에 도달하여 작업이 안전하게 자동 중단되었습니다.")
                    break

                title = article["article_title"]
                author = article["user_name"]
                url = article["url"]
                user_id = article["user_id"]
                article_no = article["article_no"]

                current_status.info(f"[{i + 1}/{total}] **'{title}'** (작가: {author}) 페이지 접속 및 우측 상단 하트 확인 중...")

                # 좋아요 수행 (우측 상단 하트 버튼 기준)
                if use_cookie:
                    res_code, msg = like_article_api(user_id, article_no, st.session_state.cookie_str, session=http_session)
                else:
                    res_code, msg = st.session_state.bot.like_article(url)

                now_str = time.strftime("%H:%M:%S")

                if res_code == "LIKED":
                    success += 1
                    article["status"] = "좋아요 완료"
                    st.session_state.completed_keys.add(url)
                    new_today = record_daily_like()
                    m_daily.metric("오늘 누적 좋아요", f"{new_today} / {DAILY_LIKE_LIMIT}회")
                    logs.append(f"[{now_str}] 💖 [성공] '{title}' ({author}) 우측 상단 하트 클릭 완료 (오늘 누적: {new_today}/{DAILY_LIKE_LIMIT}회)")

                    if new_today >= DAILY_LIKE_LIMIT:
                        logs.append(f"[{now_str}] 🛑 오늘 최대 좋아요 한도({DAILY_LIKE_LIMIT}회)를 모두 달성하였습니다!")
                        m_success.metric("성공 💖", f"{success}건")
                        progress_bar.progress((i + 1) / total)
                        log_box.code("\n".join(reversed(logs[-10:])), language="text")
                        break
                elif res_code == "ALREADY_LIKED":
                    skipped += 1
                    article["status"] = "이미 좋아요됨"
                    st.session_state.completed_keys.add(url)
                    logs.append(f"[{now_str}] ℹ️ [스킵] '{title}' ({author}) 이전에 이미 좋아요를 누른 글입니다. (즉시 다음 글로 이동)")
                elif res_code == "NOT_LOGGED_IN":
                    failed += 1
                    article["status"] = "로그인 필요"
                    logs.append(f"[{now_str}] ❌ [오류] 로그인 세션이 유효하지 않습니다: {msg}")
                    st.error("로그인이 필요합니다. [1단계]에서 카카오 로그인 또는 쿠키 입력을 진행해주세요.")
                    break
                else:
                    failed += 1
                    article["status"] = "오류"
                    logs.append(f"[{now_str}] ⚠️ [실패] '{title}': {msg}")

                # 메트릭 및 진행바 업데이트
                m_success.metric("성공 💖", f"{success}건")
                m_skip.metric("스킵(이미 누름) ℹ️", f"{skipped}건")
                m_fail.metric("실패 ❌", f"{failed}건")
                progress_bar.progress((i + 1) / total)
                log_box.code("\n".join(reversed(logs[-10:])), language="text")

                # 새로 좋아요를 누른 경우(LIKED)에만 1초 ~ 30초 무작위 지연 대기
                if res_code == "LIKED" and i < total - 1:
                    wait_time = random.randint(min_sec, max_sec)
                    for rem in range(wait_time, 0, -1):
                        countdown_box.markdown(
                            f"⏳ **다음 글까지 랜덤 대기 중:** `{rem}초` 남음 (선택된 대기 시간: **{wait_time}초** / 범위: {min_sec}~{max_sec}초)"
                        )
                        countdown_gauge.progress(rem / wait_time)
                        time.sleep(1)
                    countdown_box.empty()
                    countdown_gauge.empty()

            current_status.empty()
            st.balloons()
            st.success(f"🎉 모든 작업이 완료되었습니다! (성공: {success}건, 스킵: {skipped}건, 오류: {failed}건)")
        finally:
            if http_session:
                http_session.close()
