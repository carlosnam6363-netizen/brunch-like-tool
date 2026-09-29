"""
Brunch Like Tool - CLI Runner
명령줄(터미널)에서 브런치 특정 요일 연재글을 1분 간격으로 자동 좋아요 실행하는 도구
- 셀레니움 브라우저 모드 및 쿠키 기반 순수 API 모드 지원
"""

import os
import sys
import time
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from brunch_api import fetch_serial_articles, check_user_session, DAY_MAP, ORDER_MAP
from browser_bot import BrunchBot
from scheduler import LikeScheduler


def main():
    parser = argparse.ArgumentParser(
        description="브런치 연재글 1분 간격 자동 좋아요 도구 (Brunch Like Tool CLI)"
    )
    parser.add_argument(
        "--day",
        "-d",
        default="tue",
        choices=["mon", "tue", "wed", "thu", "fri", "sat", "sun", "com"],
        help="요일 선택 (기본: tue - 화요일)"
    )
    parser.add_argument(
        "--order",
        "-o",
        default="PUBLISH_TIME",
        choices=["PUBLISH_TIME", "POPULARITY"],
        help="정렬 기준 (기본: PUBLISH_TIME - 최신순)"
    )
    parser.add_argument(
        "--interval",
        "-i",
        type=int,
        default=60,
        help="좋아요 사이 대기 간격 (초 단위, 기본: 60초)"
    )
    parser.add_argument(
        "--cookie",
        "-c",
        default=os.getenv("BRUNCH_COOKIE"),
        help="브런치 로그인 쿠키 문자열 (지정 시 브라우저 없이 순수 HTTP로 초고속 실행)"
    )
    parser.add_argument(
        "--cookie-file",
        help="쿠키 문자열이 저장된 텍스트 파일 경로"
    )
    parser.add_argument(
        "--browser",
        "-b",
        default="chrome",
        choices=["chrome", "edge"],
        help="브라우저 종류 (기본: chrome, --cookie 미지정 시 사용)"
    )
    parser.add_argument(
        "--login",
        action="store_true",
        help="로그인 브라우저를 먼저 실행하여 세션을 저장합니다."
    )
    parser.add_argument(
        "--max-count",
        "-m",
        type=int,
        default=None,
        help="최대 좋아요 처리할 글 수 (미지정 시 전체)"
    )

    args = parser.parse_args()

    # 쿠키 파일 읽기 처리
    cookie_str = args.cookie
    if args.cookie_file and os.path.exists(args.cookie_file):
        with open(args.cookie_file, "r", encoding="utf-8") as f:
            cookie_str = f.read().strip()

    bot = None
    if not cookie_str:
        bot = BrunchBot(browser_type=args.browser)
        if args.login:
            print("\n[안내] 브런치를 열어 로그인을 진행합니다. 브라우저에서 카카오 로그인을 완료해주세요.")
            bot.open_login_window()
            input("로그인을 완료한 후 [Enter] 키를 누르면 계속 진행합니다...")
    else:
        print("[인증] 쿠키(Cookie) 모드로 실행합니다. 브라우저 없이 백그라운드에서 동작합니다.")
        is_ok, user = check_user_session(cookie_str)
        if is_ok:
            print(f"[인증 성공] '{user}' 작가님 계정으로 확인되었습니다.")
        else:
            print(f"[경고] 쿠키 세션 검증 결과: {user}")

    print(f"\n[1/3] '{args.day.upper()}' 요일 연재 글 목록을 불러옵니다 (정렬: {args.order})...")
    articles = fetch_serial_articles(day=args.day, order=args.order, max_count=args.max_count)
    if not articles:
        print("[!] 해당 요일에 올라온 연재 글이 없습니다.")
        if bot:
            bot.close()
        return

    print(f"[2/3] 총 {len(articles)}개의 연재 글을 가져왔습니다.")
    print(f"[3/3] 1분({args.interval}초) 간격으로 자동 좋아요를 시작합니다. (중단하려면 Ctrl+C)\n")

    def log_cb(msg, level):
        now = time.strftime("%H:%M:%S")
        print(f"[{now}] [{level}] {msg}")

    scheduler = LikeScheduler(
        articles=articles,
        interval_seconds=args.interval,
        bot=bot,
        cookies=cookie_str if cookie_str else None,
        log_callback=log_cb
    )

    try:
        scheduler.start()
        while scheduler.is_running:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] 사용자에 의해 중단되었습니다.")
        scheduler.stop()
    finally:
        if bot:
            bot.close()
        print("[*] 작업을 마칩니다.")


if __name__ == "__main__":
    main()
