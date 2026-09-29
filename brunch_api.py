"""
Brunch API Client Module
브런치 플랫폼 연재 글 목록 조회 및 API 기반 연동 모듈
- 순수 HTTP 요청을 통한 연재글 목록 수집
- 쿠키 세션을 이용한 직접 라이킷(좋아요) API 호출 지원 (헤드리스/클라우드 완벽 호환)
"""

import re
import time
import json
import random
import requests
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Union

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

DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Origin': 'https://brunch.co.kr',
    'Referer': 'https://brunch.co.kr/serial/list',
    'Accept': 'application/json, text/plain, */*'
}

API_BASE_URL = "https://api.brunch.co.kr"


def parse_cookie_string(cookie_input: Union[str, dict]) -> dict:
    """
    브라우저에서 복사한 쿠키 문자열 또는 딕셔너리를 파싱하여 표준 쿠키 딕셔너리로 반환합니다.
    """
    if isinstance(cookie_input, dict):
        return cookie_input

    if not cookie_input or not isinstance(cookie_input, str):
        return {}

    cookie_dict = {}
    # 'key=value; key2=value2' 형식 파싱
    for item in cookie_input.strip().split(";"):
        item = item.strip()
        if not item:
            continue
        if "=" in item:
            k, v = item.split("=", 1)
            cookie_dict[k.strip()] = v.strip()
    return cookie_dict


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
            resp = requests.get(url, headers=DEFAULT_HEADERS, params=params, timeout=15)
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

            url = next_url
            params = {}
            page += 1
            time.sleep(0.2)

        except Exception as e:
            print(f"[API Error] 글 목록 가져오기 실패: {e}")
            break

    return articles


def check_user_session(cookies: Union[str, dict]) -> Tuple[bool, Optional[str]]:
    """
    제공된 쿠키가 현재 브런치에 유효하게 로그인된 세션인지 확인합니다.
    :return: (로그인 여부 bool, 사용자명 또는 메시지)
    """
    cookie_dict = parse_cookie_string(cookies)
    if not cookie_dict:
        return False, "쿠키가 입력되지 않았습니다."

    try:
        headers = {
            'User-Agent': DEFAULT_HEADERS['User-Agent'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        resp = requests.get("https://brunch.co.kr", headers=headers, cookies=cookie_dict, timeout=10)
        if resp.status_code != 200:
            return False, f"서버 응답 코드: {resp.status_code}"

        html = resp.text
        # USER_DATA 탐색
        user_match = re.search(r'<script[^>]*id=["\']USER_DATA["\'][^>]*>(.*?)</script>', html, re.DOTALL)
        if user_match:
            try:
                user_info = json.loads(user_match.group(1))
                user_name = user_info.get("name") or user_info.get("nickname") or user_info.get("userId")
                return True, user_name
            except Exception:
                pass

        # 쿠키 내 주요 키 확인
        if "b_uid" in cookie_dict or "brunch_session" in cookie_dict:
            return True, "인증된 사용자"

        return False, "로그인 정보(USER_DATA/세션)를 찾을 수 없습니다."
    except Exception as e:
        return False, f"확인 중 오류: {str(e)}"


def like_article_api(
    user_id: str,
    article_no: int,
    cookies: Union[str, dict]
) -> Tuple[str, str]:
    """
    순수 HTTP API를 통해 특정 글에 좋아요를 누릅니다 (브라우저 없이 동작).
    1. 글 페이지를 요청하여 CSRF 보안 토큰(secure-token)과 현재 좋아요 여부(LIKE_DATA)를 획득합니다.
    2. 아직 좋아요가 눌려있지 않다면 POST https://api.brunch.co.kr/v1/likeit 요청을 보냅니다.
    
    :return: (결과 코드, 메시지)
             - 'LIKED': 좋아요 완료
             - 'ALREADY_LIKED': 이미 좋아요가 눌러진 글
             - 'NOT_LOGGED_IN': 로그인 필요 또는 세션 만료
             - 'ERROR': 기타 오류
    """
    cookie_dict = parse_cookie_string(cookies)
    if not cookie_dict:
        return "NOT_LOGGED_IN", "쿠키가 설정되지 않았습니다."

    page_url = f"https://brunch.co.kr/@@{user_id}/{article_no}"
    session = requests.Session()
    session.cookies.update(cookie_dict)

    # 1. 글 상세 페이지 조회하여 토큰 및 좋아요 상태 파악
    page_headers = {
        'User-Agent': DEFAULT_HEADERS['User-Agent'],
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }

    try:
        resp = session.get(page_url, headers=page_headers, timeout=12, allow_redirects=True)
        if resp.status_code != 200:
            return "ERROR", f"글 페이지 접근 실패 (HTTP {resp.status_code})"

        html = resp.text

        # 이미 좋아요 상태인지 확인
        like_match = re.search(r'<script[^>]*id=["\']LIKE_DATA["\'][^>]*>(.*?)</script>', html, re.DOTALL)
        if like_match:
            try:
                like_info = json.loads(like_match.group(1))
                if like_info.get("isLiked") is True:
                    return "ALREADY_LIKED", "이미 좋아요가 눌러진 글입니다 (스킵)."
            except Exception:
                pass

        # CSRF 토큰(secure-token) 추출
        token_match = re.search(r'<meta\s+name=["\']secure-token["\']\s+content=["\']([^"\']+)["\']', html)
        secure_token = token_match.group(1) if token_match else None

        # 2. POST /v1/likeit 호출
        req_id = hex(int(time.time() * 1000))[2:] + "".join(random.choices("0123456789abcdef", k=8))
        post_url = f"{API_BASE_URL}/v1/likeit"
        params = {
            "articleUserId": user_id,
            "articleNo": article_no
        }
        post_headers = {
            'User-Agent': DEFAULT_HEADERS['User-Agent'],
            'Origin': 'https://brunch.co.kr',
            'Referer': resp.url if resp.url else page_url,
            'X-BRUNCH-REQUEST-ID': req_id,
            'Accept': 'application/json, text/plain, */*'
        }
        if secure_token:
            post_headers['X-CSRF-TOKEN'] = secure_token

        like_resp = session.post(post_url, params=params, headers=post_headers, timeout=12)

        if like_resp.status_code == 200:
            return "LIKED", "좋아요를 성공적으로 눌렀습니다."
        elif like_resp.status_code == 401:
            return "NOT_LOGGED_IN", "로그인 세션이 유효하지 않습니다. 쿠키를 다시 확인해주세요."
        else:
            return "ERROR", f"좋아요 요청 실패 (HTTP {like_resp.status_code})"

    except Exception as e:
        return "ERROR", f"요청 중 오류 발생: {str(e)}"
