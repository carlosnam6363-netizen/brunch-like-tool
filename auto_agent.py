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


def get_daily_sessions(today_date, daily_limit: int) -> List[Dict]:
    """
    하루 3회 시간대 배치 스케줄을 생성합니다.
    - 각 세션당 280 ~ 300개 무작위 수량 제한 (3회 총 840~900개)
    - 아침 세션: 06:40 ~ 08:30 (280 ~ 300회)
    - 점심 세션: 12:10 ~ 13:30 (280 ~ 300회)
    - 저녁 세션: 18:40 ~ 20:30 (280 ~ 300회)
    세션 사이에는 브라우저 및 네트워크 연결을 완전히 종료하여 이상탐지를 회피합니다.
    """
    q_morning = random.randint(280, 300)
    q_lunch = random.randint(280, 300)
    q_evening = random.randint(280, 300)

    # 시작 시각에 인간적인 지터(무작위 분/초) 적용
    t_morning = datetime(today_date.year, today_date.month, today_date.day, 7, 0, 0) + timedelta(minutes=random.randint(-20, 50), seconds=random.randint(0, 59))
    t_lunch = datetime(today_date.year, today_date.month, today_date.day, 12, 30, 0) + timedelta(minutes=random.randint(-20, 40), seconds=random.randint(0, 59))
    t_evening = datetime(today_date.year, today_date.month, today_date.day, 19, 15, 0) + timedelta(minutes=random.randint(-25, 55), seconds=random.randint(0, 59))

    return [
        {"id": "morning", "name": "🌅 아침 세션", "time": t_morning, "quota": q_morning},
        {"id": "lunch", "name": "☀️ 점심 세션", "time": t_lunch, "quota": q_lunch},
        {"id": "evening", "name": "🌙 저녁 세션", "time": t_evening, "quota": q_evening},
    ]


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

    def run_today_session(self, batch_limit: Optional[int] = None, session_name: str = "단일 배치") -> bool:
        """
        오늘의 자동 좋아요 배치를 1회 실행합니다.
        - 어제의 요일 발행 글을 대상으로 수집 및 좋아요 진행
        - 세션당 280~300개 수량 제한
        - 배치 완료 시 브라우저 및 HTTP 세션 완전 종료
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
            logger.info(f"✅ 오늘 이미 목표 한도({cur_liked}/{daily_limit}회)를 모두 달성하였습니다. 금일 작업을 마칩니다.")
            self.is_running_task = False
            return True

        # 이번 배치의 목표치 결정 (배치 지정량과 당일 잔여량 중 작은 값)
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
            f"이번 세션 목표: {target_batch}회 (대상: {day_desc})"
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

        # 4. 스케줄러 실행 (가우시안 대기, 이번 배치 한도 도달 시 자동 종료)
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
            f"🏁 [{session_name} 완료] 이번 배치 성공: {success_cnt:,}건 | 스킵: {skipped_cnt:,}건 | "
            f"실패: {failed_cnt:,}건 | 오늘 총 누적: {final_today:,}/{daily_limit:,}회"
        )
        logger.info("🔒 세션/브라우저를 완전히 종료하고 다음 배치까지 휴식 상태를 유지합니다.")
        logger.info("=" * 65)
        return True

    def start_autonomous_loop(self):
        """
        24시간 상시 감시 및 3회 시간대 배치 분할 자율 실행 무한 루프
        - 아침(07:00경), 점심(12:30경), 저녁(19:15경) 각 세션당 280~300개 무작위 수량 제한
        - 각 배치 실행 후 브라우저 및 세션 완전 종료 (이상탐지 회피)
        - 대상: 어제 요일 발행 글
        """
        logger.info("=" * 65)
        logger.info("🤖 [Brunch Auto Agent] 3회 배치 분할 자율 실행 모드를 가동합니다.")
        logger.info("🛡️ 운영 설계:")
        logger.info("   1) 대상: 어제 요일 발행 글")
        logger.info("   2) 3회 배치 분할: 아침/점심/저녁 각 세션당 280~300개 무작위 제한")
        logger.info("   3) 세션 사이 브라우저 및 세션 완전 종료 (스텔스 휴식)")
        logger.info("   4) 가우시안 정규분포 딜레이 및 인간 체류 시간 모사")
        logger.info("=" * 65)

        # 시작 시 로그인 사전 점검
        is_ok, msg = self.check_auth()
        if is_ok:
            logger.info(f"✅ {msg}")
        else:
            logger.warning(f"⚠️ {msg}")

        last_executed_session_id = None
        last_executed_date = None

        while True:
            now = datetime.now()
            today_date = now.date()
            daily_limit = get_today_daily_limit()
            cur_liked = get_today_liked_count()

            # 날짜가 바뀌었으면 세션 추적 리셋
            if last_executed_date != today_date:
                last_executed_date = today_date
                last_executed_session_id = None

            # 당일 일일 한도 이미 달성 시 내일까지 대기
            if cur_liked >= daily_limit:
                tomorrow_morning = datetime(now.year, now.month, now.day, 7, 0, 0) + timedelta(days=1, minutes=random.randint(-15, 45))
                wait_sec = (tomorrow_morning - now).total_seconds()
                hours = int(wait_sec // 3600)
                mins = int((wait_sec % 3600) // 60)
                logger.info(
                    f"🎉 오늘 목표 한도({cur_liked}/{daily_limit}회)를 완수했습니다. "
                    f"내일 아침({tomorrow_morning.strftime('%m-%d %H:%M')}, 약 {hours}시간 {mins}분 후)까지 완전 휴식합니다."
                )
                while datetime.now() < tomorrow_morning:
                    time.sleep(60)
                continue

            # 오늘자 3개 세션 일정 생성
            sessions = get_daily_sessions(today_date, daily_limit)

            # 아직 실행되지 않은 다음 세션 찾기
            next_session = None
            for s in sessions:
                # 시작 시각 20분 전까지는 해당 세션의 시간창으로 간주
                if now <= s["time"] + timedelta(hours=2):
                    next_session = s
                    break

            if not next_session:
                # 오늘 모든 세션 시간(저녁 이후)이 지남 -> 내일 아침으로 대기
                tomorrow_morning = datetime(now.year, now.month, now.day, 7, 0, 0) + timedelta(days=1, minutes=random.randint(-15, 45))
                wait_sec = (tomorrow_morning - now).total_seconds()
                hours = int(wait_sec // 3600)
                mins = int((wait_sec % 3600) // 60)
                logger.info(
                    f"🌙 금일 모든 세션 시간대가 종료되었습니다. (오늘 누적: {cur_liked}/{daily_limit}회) "
                    f"내일 아침({tomorrow_morning.strftime('%m-%d %H:%M')}, 약 {hours}시간 {mins}분 후)까지 대기합니다."
                )
                while datetime.now() < tomorrow_morning:
                    time.sleep(60)
                continue

            # 다음 세션 시각까지 대기 필요 여부 확인
            if now < next_session["time"]:
                wait_seconds = (next_session["time"] - now).total_seconds()
                hours = int(wait_seconds // 3600)
                mins = int((wait_seconds % 3600) // 60)
                logger.info(
                    f"💤 [휴식 모드] 다음 배치: {next_session['name']} "
                    f"(예정: {next_session['time'].strftime('%H:%M:%S')}, 목표: {next_session['quota']}건, "
                    f"약 {hours}시간 {mins}분 대기 중... 브라우저 종료 상태)"
                )
                while datetime.now() < next_session["time"]:
                    time.sleep(30)

            # 세션 시각 도달 ➡️ 배치 실행
            logger.info(f"⏰ {next_session['name']} 실행 시각({datetime.now().strftime('%H:%M:%S')})에 도달했습니다!")
            self.run_today_session(batch_limit=next_session["quota"], session_name=next_session["name"])
            last_executed_session_id = next_session["id"]

            # 배치 완료 후 최소 10분 이상 안전 쿨다운
            time.sleep(600)


def main():
    agent = BrunchAutoAgent()

    # 명령행 인자 지원: --once 전달 시 1개 배치(280~300건)만 즉시 실행하고 종료
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        batch_quota = random.randint(280, 300)
        logger.info(f"[수동 1회 실행 모드] 안전 1회 배치({batch_quota}건 목표)를 실행합니다.")
        agent.run_today_session(batch_limit=batch_quota, session_name="수동 단일 배치")
    else:
        agent.start_autonomous_loop()


if __name__ == "__main__":
    main()
