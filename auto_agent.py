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


def get_yesterday_day_code(base_date: Optional[datetime] = None) -> Tuple[str, str]:
    """
    어제 날짜에 해당하는 브런치 요일 코드(mon~sun) 및 한국어 명칭 반환
    예: 오늘이 목요일이면 어제는 수요일 -> ('wed', '수요일')
    """
    target_date = (base_date or datetime.now()) - timedelta(days=1)
    days_en = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    days_ko = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
    w = target_date.weekday()
    return days_en[w], days_ko[w]


class BrunchAutoAgent:
    def __init__(self, target_days: Optional[List[str]] = None):
        # target_days가 명시되지 않은 경우 어제 요일을 동적으로 계산하여 타겟팅
        self._custom_days = target_days is not None
        self.target_days = target_days or []
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

    def run_today_session(self, batch_limit: Optional[int] = None, session_name: str = "수동 실행") -> bool:
        """
        좋아요 세션을 1회 실행합니다. (시간대별 자동 예약 실행 제거됨)
        - 어제의 요일 발행 글을 대상으로 수집 및 좋아요 진행
        - 일일 한도(1,400회) 내에서 동작
        """
        if self.is_running_task:
            logger.warning("이미 작업이 실행 중입니다.")
            return False

        self.is_running_task = True
        today_str = get_today_str()
        daily_limit = get_today_daily_limit()
        cur_liked = get_today_liked_count()

        # 잔여 허용량 계산
        remaining_today = max(0, daily_limit - cur_liked)
        if remaining_today <= 0:
            logger.info(f"✅ 오늘 이미 목표 한도({cur_liked}/{daily_limit}회)를 모두 달성하였습니다. 작업을 마칩니다.")
            self.is_running_task = False
            return True

        # 이번 실행의 목표치 결정
        target_batch = min(batch_limit or remaining_today, remaining_today)

        # 대상 요일 결정 (기본: 어제 요일)
        if not self._custom_days:
            y_code, y_kor = get_yesterday_day_code()
            target_days = [y_code]
            day_desc = f"어제({y_kor}) 발행 글"
        else:
            target_days = self.target_days
            day_desc = f"{', '.join(target_days)} 요일 글"

        logger.info("=" * 65)
        logger.info(f"🚀 [Brunch Auto Agent] {today_str} [{session_name}] 가동")
        logger.info(
            f"🎯 일일 최대 한도: {daily_limit}회 | 현재 누적: {cur_liked}회 | "
            f"이번 실행 목표: {target_batch}회 (대상: {day_desc})"
        )
        logger.info("=" * 65)

        # 1. 계정 인증 확인
        is_ok, auth_msg = self.check_auth()
        if not is_ok:
            logger.error(f"❌ [로그인 오류] {auth_msg}")
            logger.error("👉 해결 방법: PC에서 'run_gui.bat' 또는 'run_web.bat'을 열고 1회 로그인해주세요.")
            self.is_running_task = False
            return False

        logger.info(f"🔑 {auth_msg}")

        # 2. 글 목록 수집 (어제 요일 기준)
        logger.info(f"📋 연재 글 목록을 수집하는 중... (대상: {day_desc})")
        try:
            articles = fetch_multiple_days_articles(
                days=target_days,
                order="PUBLISH_TIME",
                progress_callback=lambda msg, count=None: None
            )
            logger.info(f"총 {len(articles):,}개의 {day_desc} 목록을 정상 수집했습니다.")
        except Exception as e:
            logger.error(f"❌ 글 목록 수집 실패: {e}")
            self.is_running_task = False
            return False

        # 3. 기완료 건 필터링
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

        # 4. 스케줄러 실행
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
            batch_limit=target_batch,
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
            f"🏁 [{session_name} 완료] 성공: {success_cnt:,}건 | 스킵: {skipped_cnt:,}건 | "
            f"실패: {failed_cnt:,}건 | 오늘 총 누적: {final_today:,}/{daily_limit:,}회"
        )
        logger.info("=" * 65)
        return True


def main():
    agent = BrunchAutoAgent()
    logger.info("[수동 실행 모드] 시간대별 자동 예약 없이 즉시 1회 실행합니다.")
    agent.run_today_session(session_name="수동 실행")


if __name__ == "__main__":
    main()
