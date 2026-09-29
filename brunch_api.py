"""
Brunch API Client Module
브런치 플랫폼 연재 글 목록 조회 및 API 기반 연동 모듈
"""

import time
import random
import requests
from datetime import datetime
from typing import List, Dict, Optional, Tuple

DAY_MAP = {
    "mon": "MONDAY",
    "tue": "TUESDAY",
    "wed": "WEDNESDAY",
    "thu": "THURSDAY",
    "fri": "FRIDAY",
    "sat": "SATURDAY",
    "sun": "SUNDAY",
    "com": "COMPLETE",
    # Korean names
    "월": "MONDAY",
    "화": "TUESDAY",
    "수": "WEDNESDAY",
    "목": "THURSDAY",
    "금": "FRIDAY",
    "토": "SATURDAY",
    "일": "SUNDAY",
    "완결": "COMPLETE",
    # Full names
    "MONDAY": "MONDAY",
    "TUESDAY": "TUESDAY",
    "WEDNESDAY": "WEDNESDAY",
    "THURSDAY": "THURSDAY",
    "FRIDAY": "FRIDAY",
    "SATURDAY": "SATURDAY",
    "SUNDAY": "SUNDAY",
    "COMPLETE": "COMPLETE"
}

ORDER_MAP = {
    "최신순": "PUBLISH_TIME",
    "인기순": "POPULARITY",
    "PUBLISH_TIME": "PUBLISH_TIME",
    "POPULARITY": "POPULARITY"
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Origin': 'https://brunch.co.kr',
    'Referer': 'https://brunch.co.kr/serial/list',
    'Accept': 'application/json, text/plain, */*'
}

API_BASE_URL = "https://api.brunch.co.kr"


def format_timestamp(ts_ms: Optional[int]) -> str:
    """밀리초 타임스탬프를 읽기 쉬운 일시 문자열로 변환합니다."""
    if not ts_ms:
        return "-"
    try:
        dt = datetime.fromtimestamp(ts_ms / 1000.0)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(ts_ms)


def fetch_serial_articles(
    day: str = "tue",
    order: str = "PUBLISH_TIME",
    max_count: Optional[int] = None,
    progress_callback: Optional[callable] = None
) -> List[Dict]:
    """
    브런치 연재 목록 API(https://api.brunch.co.kr/v2/serial-brunchbook/all)를 호출하여
    지정된 요일과 정렬 기준의 글 목록을 전부 가져옵니다.

    :param day: 요일 코드 ('tue', 'mon', 'wed', 'thu', 'fri', 'sat', 'sun', 'com' 또는 한글)
    :param order: 정렬 기준 ('PUBLISH_TIME' 또는 'POPULARITY')
    :param max_count: 최대 수집 개수 (None이면 전체 수집)
    :param progress_callback: 진행 상황 알림 콜백 (func(current_count))
    :return: 수집된 글 정보 딕셔너리 리스트
    """
    day_code = DAY_MAP.get(day, "TUESDAY")
    order_code = ORDER_MAP.get(order, "PUBLISH_TIME")

    url = f"{API_BASE_URL}/v2/serial-brunchbook/all"
    params = {
        "dayOfWeek": day_code,
        "orderKeyword": order_code,
        "serialStatus": "COMPLETE" if day_code == "COMPLETE" else "ONGOING"
    }

    articles = []
    page = 1

    while True:
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
            if resp.status_code != 200:
                break

            result = resp.json()
            data = result.get("data", {})
            items = data.get("list", [])
            if not items:
                break

            for item in items:
                user_id = item.get("userId", "")
                article_no = item.get("articleNo", 0)
                article_url = f"https://brunch.co.kr/@@{user_id}/{article_no}"

                articles.append({
                    "user_id": user_id,
                    "user_name": item.get("userName", ""),
                    "magazine_no": item.get("magazineNo", 0),
                    "magazine_title": item.get("magazineTitle", ""),
                    "article_no": article_no,
                    "article_title": item.get("articleTitle", ""),
                    "article_sub_title": item.get("articleSubTitle", ""),
                    "publish_time": item.get("publishTime"),
                    "publish_date_str": format_timestamp(item.get("publishTime")),
                    "like_count": item.get("likeCount", 0),
                    "url": article_url,
                    "status": "대기중"
                })

                if max_count and len(articles) >= max_count:
                    break

            if progress_callback:
                progress_callback(len(articles))

            if max_count and len(articles) >= max_count:
                break

            has_more = data.get("moreList", False)
            next_url = data.get("nextUrl")

            if not has_more or not next_url:
                break

            # 다음 페이지 URL로 업데이트 (next_url에 쿼리스트링이 포함되어 있으므로 params 초기화)
            url = next_url
            params = {}
            page += 1
            time.sleep(0.2)  # API 과부하 방지 딜레이

        except Exception as e:
            print(f"[API Error] 글 목록 가져오기 실패: {e}")
            break

    return articles
