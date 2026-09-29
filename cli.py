"""
Brunch Like Tool - CLI Runner
명령줄(터미널)에서 브런치 특정 요일 연재글을 1분 간격으로 자동 좋아요 실행하는 도구
"""

import os
import sys
import time
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from brunch_api import fetch_serial_articles, DAY_MAP, ORDER_MAP
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
        "--browser",
        "-b",
        default="chrome",
        choices=["chrome", "edge"],
        help="브라우저 종류 (기본: chrome)"
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

    bot = BrunchBot(browser_type=args.browser)

    if args.login:
        print("\n[안내] 브런치를 열어 로그인을 진행합니다. 브라우저에서 카카오 로그인을 완료해주세요.")
        bot.open_login_window()
        input("로그인을 완료한 후 [Enter] 키를 누르면 계속 진행합니다...")

    print(f"\n[1/3] '{args.day.upper()}' 요일 연재 글 목록을 불러옵니다 (정렬: {args.order})...")
    articles = fetch_serial_articles(day=args.day, order=args.order, max_count=args.max_count)
    if not articles:
        print("[!] 해당 요일에 올라온 연재 글이 없습니다.")
        bot.close()
        return

    print(f"[2/3] 총 {len(articles)}개의 연재 글을 가져왔습니다.")
    print(f"[3/3] 1분({args.interval}초) 간격으로 자동 좋아요를 시작합니다. (중단하려면 Ctrl+C)")

    def log_cb(msg, level):
        now = time.strftime("%H:%M:%S")
        print(f"[{now}] [{level}] {msg}")

    scheduler = LikeScheduler(
        bot=bot,
        articles=articles,
        interval_seconds=args.interval,
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
        bot.close()
        print("[*] 브라우저를 종료하고 작업을 마칩니다.")


if __name__ == "__main__":
    main()
