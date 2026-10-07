"""
Brunch Auto Agent
매일 아침 06:00 ~ 08:00 사이 무작위 시각에 자동 실행되는 브런치 좋아요 에이전트
- 사람처럼 자연스러운 패턴:
  1) 매일 06:00 ~ 08:00 사이 무작위 시각 자동 기상 및 실행
  2) 글마다 1초 ~ 30초 사이 무작위 간격 지연
  3) 1일 최대 좋아요 수량: 1,450 ~ 1,500개 사이로 매일 랜덤 자동 조절
- 원격 개입 불필요 (Zero-touch Autonomous Mode)
- 정전/PC 재부팅/절전 복구 자동 대응 (미실행 감지 시 자동 실행)
- 로컬 DB(brunch_profile/completed_articles.json, daily_like_stats.json) 100% 연동
"""

import os
import sys
import time
import json
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from brunch_api import fetch_multiple_days_articles, check_user_session, parse_cookie_string
from scheduler import LikeScheduler
from daily_stats import (
    get_today_str,
    get_today_liked_count,
    get_today_daily_limit,
    record_daily_like,
    can_like_today,
    load_daily_stats
)

PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brunch_profile")
os.makedirs(PROFILE_DIR, exist_ok=True)
CACHE_FILE = os.path.join(PROFILE_DIR, "completed_articles.json")
COOKIE_FILE = os.path.join(PROFILE_DIR, "last_cookie.txt")
LOG_FILE = os.path.join(PROFILE_DIR, "auto_agent.log")

# 로깅 설정 (콘솔 및 파일 동시 출력)
logger = logging.getLogger("BrunchAutoAgent")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(formatter)
logger.addHandler(ch)

fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
fh.setFormatter(formatter)
logger.addHandler(fh)


def load_cookie() -> str:
    """저장된 브런치 로그인 쿠키를 불러옵니다."""
    env_cookie = os.getenv("BRUNCH_COOKIE", "")
    if env_cookie:
        return env_cookie.strip()

    if os.path.exists(COOKIE_FILE):
        try:
            with open(COOKIE_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    return content
        except Exception:
            pass

    # fallback: brunch_profile 내 Chrome 세션에서 쿠키 자동 추출 시도
    try:
        from browser_bot import BrunchBot
        logger.info("🔍 저장된 쿠키 파일이 없어 Chrome 프로필에서 세션 쿠키 자동 추출을 시도합니다...")
        bot = BrunchBot(browser_type="chrome", profile_dir=PROFILE_DIR)
        driver = bot.init_driver(headless=True)
        driver.get("https://brunch.co.kr")
        time.sleep(2)
        cookies = driver.get_cookies()
        bot.close()

        cookie_parts = []
        for c in cookies:
            cookie_parts.append(f"{c['name']}={c['value']}")
        cookie_str = "; ".join(cookie_parts)
        if "b_uid" in cookie_str or "brunch_session" in cookie_str:
            with open(COOKIE_FILE, "w", encoding="utf-8") as f:
                f.write(cookie_str)
            logger.info("✨ Chrome 프로필로부터 로그인 쿠키 추출 및 저장(last_cookie.txt)을 완료했습니다.")
            return cookie_str
    except Exception as e:
        logger.warning(f"Chrome 프로필 쿠키 자동 추출 실패: {e}")

    return ""


def load_completed_cache() -> Tuple[set, list]:
    """기존 완료 목록 로드"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data.get("keys", [])), data.get("articles", [])
        except Exception:
            pass
    return set(), []


def save_completed_cache(completed_keys: set, completed_articles: list):
    """완료 목록 저장"""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "keys": list(completed_keys),
                "articles": completed_articles
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"완료 캐시 저장 실패: {e}")


def calculate_next_morning_time(base_date: Optional[datetime] = None) -> datetime:
    """
    지정된 날짜(기본: 내일)의 오전 06:00 실행 시각을 계산합니다.
    (사람처럼 자연스러운 패턴을 위해 06:00:00부터 06:03:00 사이 미세 지터 적용)
    """
    now = base_date or datetime.now()
    rand_sec = random.randint(0, 180)  # 0초 ~ 3분 미세 랜덤
    target = datetime(now.year, now.month, now.day, 6, 0, 0) + timedelta(seconds=rand_sec)
    return target


class BrunchAutoAgent:
    def __init__(self, target_days: Optional[List[str]] = None):
        # 기본값: 전체 요일 (월, 화, 수, 목, 금, 토, 일, 완결작)
        self.target_days = target_days or ["mon", "tue", "wed", "thu", "fri", "sat", "sun", "com"]
        self.cookie = load_cookie()
        self.completed_keys, self.completed_articles = load_completed_cache()
        self.is_running_task = False

    def check_auth(self) -> Tuple[bool, str]:
        """로그인 세션 검증"""
        self.cookie = load_cookie()
        if not self.cookie:
            return False, "저장된 쿠키가 없습니다. (run_gui.bat 또는 app.py에서 최초 1회 로그인 필요)"

        is_ok, user = check_user_session(self.cookie)
        if is_ok:
            return True, f"'{user}' 작가님 계정 인증 성공"
        return False, f"인증 실패: {user}"

    def run_today_session(self) -> bool:
        """
        오늘의 자동 좋아요 세션을 1회 실행합니다.
        - 매일 1,450 ~ 1,500회 사이의 새로운 랜덤 목표치 자동 적용
        - 1초 ~ 30초 사이 랜덤 간격 좋아요 처리
        """
        if self.is_running_task:
            logger.warning("이미 작업이 실행 중입니다.")
            return False

        self.is_running_task = True
        today_str = get_today_str()
        daily_limit = get_today_daily_limit()
        cur_liked = get_today_liked_count()

        logger.info("=" * 65)
        logger.info(f"🚀 [Brunch Auto Agent] {today_str} 자동 좋아요 세션을 시작합니다.")
        logger.info(f"🎯 오늘 목표 한도: {daily_limit:,}회 (1,450~1,500회 랜덤 배정) | 현재 누적: {cur_liked:,}회")
        logger.info("=" * 65)

        # 1. 일일 한도 사전 검사
        if cur_liked >= daily_limit:
            logger.info(f"✅ 오늘 이미 목표 한도({cur_liked}/{daily_limit}회)를 모두 달성하였습니다. 금일 작업을 마칩니다.")
            self.is_running_task = False
            return True

        # 2. 계정 인증 확인
        is_ok, auth_msg = self.check_auth()
        if not is_ok:
            logger.error(f"❌ [로그인 오류] {auth_msg}")
            logger.error("👉 해결 방법: PC에서 'run_gui.bat' 또는 'run_web.bat'을 열고 1회 로그인해주세요.")
            self.is_running_task = False
            return False

        logger.info(f"🔑 {auth_msg}")

        # 3. 글 목록 수집 (전체 요일)
        logger.info(f"📋 연재 글 목록을 수집하는 중... (대상 요일: {', '.join(self.target_days)})")
        try:
            articles = fetch_multiple_days_articles(
                days=self.target_days,
                order="PUBLISH_TIME",
                progress_callback=lambda msg, count=None: None
            )
            logger.info(f"총 {len(articles):,}개의 연재 글을 수집했습니다.")
        except Exception as e:
            logger.error(f"❌ 글 목록 수집 실패: {e}")
            self.is_running_task = False
            return False

        # 4. 기완료 건 필터링
        self.completed_keys, self.completed_articles = load_completed_cache()
        pending = []
        for art in articles:
            key = f"{art.get('user_id')}_{art.get('article_no')}"
            if key not in self.completed_keys and art.get("status") not in ("좋아요 완료", "이미 좋아요됨"):
                pending.append(art)

        logger.info(f"필터링 결과: 대기 {len(pending):,}건 / 기완료 {len(self.completed_keys):,}건")
        if not pending:
            logger.info("🎉 현재 대기 중인 모든 글의 좋아요가 이미 완료되었습니다.")
            self.is_running_task = False
            return True

        # 5. 스케줄러 실행 (1초~30초 랜덤 대기, 일일 랜덤 한도 도달 시 자동 중단)
        success_cnt = 0
        skipped_cnt = 0
        failed_cnt = 0

        def on_article_done(art: Dict, status_str: str):
            nonlocal success_cnt, skipped_cnt
            key = f"{art.get('user_id')}_{art.get('article_no')}"
            if key not in self.completed_keys:
                self.completed_keys.add(key)
                art["status"] = status_str
                art["done_time"] = datetime.now().strftime("%H:%M:%S")
                self.completed_articles.insert(0, art)
                save_completed_cache(self.completed_keys, self.completed_articles)

        def log_cb(msg: str, level: str = "INFO"):
            if level in ("SUCCESS", "WARN", "ERROR"):
                logger.info(f"[{level}] {msg}")

        scheduler = LikeScheduler(
            articles=pending,
            interval_min=1,
            interval_max=30,
            cookies=self.cookie,
            daily_limit=daily_limit,
            log_callback=log_cb,
            article_completed_callback=on_article_done
        )

        try:
            scheduler._run_loop()
            success_cnt = scheduler.success_count
            skipped_cnt = scheduler.skipped_count
            failed_cnt = scheduler.failed_count
        except Exception as e:
            logger.error(f"실행 중 예외 발생: {e}")
        finally:
            self.is_running_task = False

        final_today = get_today_liked_count()
        logger.info("=" * 65)
        logger.info(
            f"🏁 [세션 종료] 성공: {success_cnt:,}건 | 스킵: {skipped_cnt:,}건 | 실패: {failed_cnt:,}건 | "
            f"오늘 누적: {final_today:,}/{daily_limit:,}회"
        )
        logger.info("=" * 65)
        return True

    def start_autonomous_loop(self):
        """
        24시간 상시 감시 및 아침 06:00 ~ 08:00 자동 실행 무한 루프
        - PC가 켜져 있으면 매일 아침 정해진 랜덤 시간에 스스로 깨어나 작업 수행
        - 정전/재부팅 복구 지원: 오늘 아직 실행 안 되었으면 즉시 1회 실행 후 내일 스케줄 진입
        """
        logger.info("=" * 65)
        logger.info("🤖 [Brunch Auto Agent] 자동 실행 데몬 모드를 가동합니다.")
        logger.info("⏰ 매일 아침 06:00에 자동으로 깨어나 좋아요를 실행합니다.")
        logger.info("🎲 일일 최대 좋아요: 1,450 ~ 1,500회 사이 매일 랜덤 한도 적용")
        logger.info("⏱️ 각 글 처리 간격: 1초 ~ 30초 사이 랜덤 지연")
        logger.info("=" * 65)

        # 시작 시 로그인 사전 점검
        is_ok, msg = self.check_auth()
        if is_ok:
            logger.info(f"✅ {msg}")
        else:
            logger.warning(f"⚠️ {msg}")

        while True:
            now = datetime.now()
            today_str = get_today_str()
            cur_liked = get_today_liked_count()
            daily_limit = get_today_daily_limit()

            # 오늘 아직 목표치에 도달하지 않았고, 현재 시각이 06:00 이후이거나 미실행(0건)이라면 오늘 세션 우선 실행
            if cur_liked < daily_limit:
                if (now.hour >= 6) or (cur_liked == 0):
                    logger.info("⚡ 금일 실행 조건을 만족하여 자동 세션을 가동합니다.")
                    self.run_today_session()
                    # 실행 후 시간 재확인
                    now = datetime.now()

            # 내일 아침 06:00 다음 실행 목표 시각 계산
            tomorrow = now + timedelta(days=1)
            next_wake_time = calculate_next_morning_time(tomorrow)

            # 만약 오늘 아직 06시 이전이라면, 오늘 아침 시각으로 설정
            if now.hour < 6 and cur_liked < daily_limit:
                today_wake = calculate_next_morning_time(now)
                if today_wake > now:
                    next_wake_time = today_wake

            wait_seconds = (next_wake_time - now).total_seconds()
            hours = int(wait_seconds // 3600)
            mins = int((wait_seconds % 3600) // 60)

            logger.info(
                f"💤 다음 자동 실행 예정: {next_wake_time.strftime('%Y-%m-%d %H:%M:%S')} "
                f"(약 {hours}시간 {mins}분 후 대기 중...)"
            )

            # 대기 루프 (30초마다 상태 점검 및 깨어남 감지)
            while datetime.now() < next_wake_time:
                time.sleep(30)

            # 기상 시각 도달 ➡️ 세션 실행
            logger.info(f"⏰ 예약된 기상 시각({next_wake_time.strftime('%H:%M:%S')})에 도달했습니다!")
            self.run_today_session()
            time.sleep(60)


def main():
    agent = BrunchAutoAgent()

    # 명령행 인자 지원: --once 전달 시 1회만 즉시 실행하고 종료
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        logger.info("[수동 실행 모드] 오늘의 세션을 1회 즉시 실행합니다.")
        agent.run_today_session()
    else:
        agent.start_autonomous_loop()


if __name__ == "__main__":
    main()
