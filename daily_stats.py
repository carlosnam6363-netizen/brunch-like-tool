"""
Daily Stats Module
매일 좋아요 누적 횟수 관리 및 일일 최대 한도(1,498회) 제어
- 로컬 JSON 영구 파일에 일별 누적치 자동 기록 (날짜 변경 시 자동 리셋 및 이력 보관)
- 멀티스레드 안전성 보장 (스레드 락)
"""

import os
import json
import threading
from datetime import datetime
from typing import Dict, Tuple

DAILY_LIKE_LIMIT = 1498

_lock = threading.Lock()
_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brunch_profile")
_STATS_FILE = os.path.join(_CACHE_DIR, "daily_like_stats.json")


def get_today_str() -> str:
    """오늘 날짜 (YYYY-MM-DD) 반환"""
    return datetime.now().strftime("%Y-%m-%d")


def _ensure_dir():
    os.makedirs(_CACHE_DIR, exist_ok=True)


def load_daily_stats() -> Dict:
    """
    일일 통계 데이터를 로드합니다.
    자정이 지나 날짜가 변경되었으면 기존 날짜 데이터를 history로 이동하고 오늘의 카운트를 0으로 자동 갱신합니다.
    """
    _ensure_dir()
    today = get_today_str()
    data = {"date": today, "count": 0, "history": {}}

    with _lock:
        if os.path.exists(_STATS_FILE):
            try:
                with open(_STATS_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    if isinstance(saved, dict):
                        saved_date = saved.get("date", today)
                        saved_count = saved.get("count", 0)
                        history = saved.get("history", {})

                        if saved_date == today:
                            data = {
                                "date": today,
                                "count": max(0, int(saved_count)),
                                "history": history
                            }
                        else:
                            # 날짜가 변경된 경우 이전 날짜 기록 보존 후 오늘 카운트 0으로 리셋
                            if saved_date and saved_count:
                                history[saved_date] = saved_count
                            data = {
                                "date": today,
                                "count": 0,
                                "history": history
                            }
                            # 갱신된 내용 즉시 저장
                            with open(_STATS_FILE, "w", encoding="utf-8") as wf:
                                json.dump(data, wf, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[DailyStats] 로드 실패: {e}")
                data = {"date": today, "count": 0, "history": {}}
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


def record_daily_like() -> int:
    """
    좋아요 성공 시 오늘 카운트를 1 증가시키고 저장합니다.
    :return: 증가된 오늘의 총 누적 좋아요 수
    """
    _ensure_dir()
    today = get_today_str()

    with _lock:
        stats = {"date": today, "count": 0, "history": {}}
        if os.path.exists(_STATS_FILE):
            try:
                with open(_STATS_FILE, "r", encoding="utf-8") as f:
                    stats = json.load(f)
            except Exception:
                stats = {"date": today, "count": 0, "history": {}}

        saved_date = stats.get("date", today)
        history = stats.get("history", {})
        if saved_date == today:
            new_count = int(stats.get("count", 0)) + 1
        else:
            old_count = stats.get("count", 0)
            if saved_date and old_count:
                history[saved_date] = old_count
            new_count = 1

        stats["date"] = today
        stats["count"] = new_count
        stats["history"] = history
        stats["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            with open(_STATS_FILE, "w", encoding="utf-8") as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[DailyStats] 저장 실패: {e}")

        return new_count


def reset_today_liked_count() -> None:
    """오늘 좋아요 카운트를 수동으로 0으로 초기화합니다."""
    _ensure_dir()
    today = get_today_str()

    with _lock:
        stats = {"date": today, "count": 0, "history": {}}
        if os.path.exists(_STATS_FILE):
            try:
                with open(_STATS_FILE, "r", encoding="utf-8") as f:
                    stats = json.load(f)
            except Exception:
                pass

        stats["date"] = today
        stats["count"] = 0
        stats["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            with open(_STATS_FILE, "w", encoding="utf-8") as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


def can_like_today(limit: int = DAILY_LIKE_LIMIT) -> Tuple[bool, int, int]:
    """
    오늘 좋아요 추가 실행 가능 여부를 판별합니다.
    :return: (실행가능여부, 오늘누적수, 잔여가능수)
    """
    cnt = get_today_liked_count()
    remaining = max(0, limit - cnt)
    return (cnt < limit), cnt, remaining
