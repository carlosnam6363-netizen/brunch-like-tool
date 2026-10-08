"""
Daily Stats Module
매일 좋아요 누적 횟수 관리 및 일일 최대 한도(1,450 ~ 1,500회 사이 랜덤) 제어
- 매일 1,450 ~ 1,500회 사이의 무작위 목표치가 자동 생성되어 사람처럼 자연스럽게 작동
- 로컬 JSON 영구 파일에 일별 누적치 및 당일 목표치 자동 기록 (날짜 변경 시 자동 리셋 및 이력 보관)
- 멀티스레드 안전성 보장 (스레드 락)
"""

import os
import json
import random
import threading
from datetime import datetime
from typing import Dict, Tuple, Optional

DAILY_LIMIT_MIN = 1400
DAILY_LIMIT_MAX = 1400

_lock = threading.Lock()
_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brunch_profile")
_STATS_FILE = os.path.join(_CACHE_DIR, "daily_like_stats.json")


def get_today_str() -> str:
    """오늘 날짜 (YYYY-MM-DD) 반환"""
    return datetime.now().strftime("%Y-%m-%d")


def _ensure_dir():
    os.makedirs(_CACHE_DIR, exist_ok=True)


def _generate_random_limit() -> int:
    """1,450 ~ 1,500회 사이의 자연스러운 일일 한도 랜덤 생성"""
    return random.randint(DAILY_LIMIT_MIN, DAILY_LIMIT_MAX)


def load_daily_stats() -> Dict:
    """
    일일 통계 데이터를 로드합니다.
    자정이 지나 날짜가 변경되었으면 기존 날짜 데이터를 history로 이동하고 오늘의 카운트를 0으로 자동 갱신합니다.
    매일 1,450~1,500회 사이의 새 랜덤 한도가 배정됩니다.
    """
    _ensure_dir()
    today = get_today_str()
    data = {
        "date": today,
        "count": 0,
        "daily_limit": _generate_random_limit(),
        "history": {}
    }

    with _lock:
        if os.path.exists(_STATS_FILE):
            try:
                with open(_STATS_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    if isinstance(saved, dict):
                        saved_date = saved.get("date", today)
                        saved_count = saved.get("count", 0)
                        history = saved.get("history", {})
                        saved_limit = saved.get("daily_limit")

                        if saved_date == today:
                            # 오늘 한도가 이미 있으면 유지, 없거나 범위를 벗어나면 새로 생성
                            if not saved_limit or not (DAILY_LIMIT_MIN <= saved_limit <= DAILY_LIMIT_MAX):
                                saved_limit = _generate_random_limit()

                            data = {
                                "date": today,
                                "count": max(0, int(saved_count)),
                                "daily_limit": saved_limit,
                                "history": history
                            }
                        else:
                            # 날짜가 변경된 경우 이전 날짜 기록 보존 후 오늘 카운트 0으로 리셋 및 새 랜덤 한도 배정
                            if saved_date and saved_count:
                                history[saved_date] = {
                                    "count": saved_count,
                                    "daily_limit": saved_limit or 1498
                                }
                            new_limit = _generate_random_limit()
                            data = {
                                "date": today,
                                "count": 0,
                                "daily_limit": new_limit,
                                "history": history
                            }
                            # 갱신된 내용 즉시 저장
                            with open(_STATS_FILE, "w", encoding="utf-8") as wf:
                                json.dump(data, wf, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[DailyStats] 로드 실패: {e}")
                data = {
                    "date": today,
                    "count": 0,
                    "daily_limit": _generate_random_limit(),
                    "history": {}
                }
        else:
            try:
                with open(_STATS_FILE, "w", encoding="utf-8") as wf:
                    json.dump(data, wf, ensure_ascii=False, indent=2)
            except Exception:
                pass

    return data


def get_today_liked_count() -> int:
    """오늘 누적 좋아요 횟수 반환"""
    stats = load_daily_stats()
    return stats.get("count", 0)


def get_today_daily_limit() -> int:
    """오늘 배정된 일일 목표치(1,400회) 반환"""
    stats = load_daily_stats()
    return stats.get("daily_limit", 1400)


def record_daily_like() -> int:
    """
    좋아요 성공 시 오늘 카운트를 1 증가시키고 저장합니다.
    :return: 증가된 오늘의 총 누적 좋아요 수
    """
    _ensure_dir()
    today = get_today_str()

    with _lock:
        stats = {
            "date": today,
            "count": 0,
            "daily_limit": _generate_random_limit(),
            "history": {}
        }
        if os.path.exists(_STATS_FILE):
            try:
                with open(_STATS_FILE, "r", encoding="utf-8") as f:
                    stats = json.load(f)
            except Exception:
                pass

        saved_date = stats.get("date", today)
        history = stats.get("history", {})
        saved_limit = stats.get("daily_limit")
        if not saved_limit or not (DAILY_LIMIT_MIN <= saved_limit <= DAILY_LIMIT_MAX):
            saved_limit = _generate_random_limit()

        if saved_date == today:
            new_count = int(stats.get("count", 0)) + 1
        else:
            old_count = stats.get("count", 0)
            if saved_date and old_count:
                history[saved_date] = {
                    "count": old_count,
                    "daily_limit": saved_limit
                }
            new_count = 1
            saved_limit = _generate_random_limit()

        stats["date"] = today
        stats["count"] = new_count
        stats["daily_limit"] = saved_limit
        stats["history"] = history
        stats["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            with open(_STATS_FILE, "w", encoding="utf-8") as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[DailyStats] 저장 실패: {e}")

        return new_count


def reset_today_liked_count() -> None:
    """오늘 좋아요 카운트를 수동으로 0으로 초기화합니다 (한도는 새로 랜덤 재추첨)."""
    _ensure_dir()
    today = get_today_str()

    with _lock:
        stats = {"date": today, "count": 0, "daily_limit": _generate_random_limit(), "history": {}}
        if os.path.exists(_STATS_FILE):
            try:
                with open(_STATS_FILE, "r", encoding="utf-8") as f:
                    stats = json.load(f)
            except Exception:
                pass

        stats["date"] = today
        stats["count"] = 0
        stats["daily_limit"] = _generate_random_limit()
        stats["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            with open(_STATS_FILE, "w", encoding="utf-8") as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


def can_like_today(limit: Optional[int] = None) -> Tuple[bool, int, int]:
    """
    오늘 좋아요 추가 실행 가능 여부를 판별합니다.
    :param limit: 지정되지 않으면 오늘 자동 배정된 1450~1500 랜덤 한도 기준
    :return: (실행가능여부, 오늘누적수, 잔여가능수)
    """
    if limit is None:
        limit = get_today_daily_limit()
    cnt = get_today_liked_count()
    remaining = max(0, limit - cnt)
    return (cnt < limit), cnt, remaining


# 호환성을 위한 기본 상수 (동적 조회는 get_today_daily_limit() 사용 권장)
DAILY_LIKE_LIMIT = 1400
