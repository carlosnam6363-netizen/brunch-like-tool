"""
Brunch Like Tool - CLI Runner
명령줄(터미널) 및 GitHub Actions에서 브런치 특정 요일 연재글을 랜덤/지정 간격으로 자동 좋아요 실행하는 도구
- 셀레니움 브라우저 모드 및 쿠키 기반 순수 API 모드 지원
- GitHub Actions ($GITHUB_STEP_SUMMARY) 마크다운 리포트 자동 생성
- 우측 상단 하트 버튼 기준 타겟팅
"""

import os
import sys
import time
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from brunch_api import fetch_serial_articles, check_user_session, normalize_day, normalize_order
from browser_bot import BrunchBot
from scheduler import LikeScheduler


def main():
    parser = argparse.ArgumentParser(
        description="브런치 연재글 자동 좋아요 도구 (Brunch Like Tool CLI)"
    )
    parser.add_argument(
        "--day",
        "-d",
        default="tue",
        help="요일 선택 (mon, tue, wed, thu, fri, sat, sun, com 또는 한글, 기본: tue)"
    )
    parser.add_argument(
        "--order",
        "-o",
        default="PUBLISH_TIME",
        choices=["PUBLISH_TIME", "POPULARITY"],
        help="정렬 기준 (기본: PUBLISH_TIME - 최신순)"
    )
    parser.add_argument(
        "--min-interval",
        type=int,
        default=1,
        help="좋아요 사이 최소 대기 초 (랜덤 간격, 기본: 1초)"
    )
    parser.add_argument(
        "--max-interval",
        type=int,
        default=30,
        help="좋아요 사이 최대 대기 초 (랜덤 간격, 기본: 30초)"
    )
    parser.add_argument(
        "--interval",
        "-i",
        type=int,
        default=None,
        help="고정 대기 간격 (초 단위, 지정 시 min/max 대신 고정값 사용)"
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
        help="최대 좋아요 처리할 글 수 (미지정 또는 0이면 전체)"
    )

    args = parser.parse_args()
    max_count = args.max_count if (args.max_count and args.max_count > 0) else None

    # 쿠키 파일 읽기 처리
    cookie_str = args.cookie
    if args.cookie_file and os.path.exists(args.cookie_file):
        with open(args.cookie_file, "r", encoding="utf-8") as f:
            cookie_str = f.read().strip()

    bot = None
    if not cookie_str:
        # GitHub Actions 환경인지 확인 (헤드리스 브라우저 창 불가 안내)
        if os.getenv("GITHUB_ACTIONS") == "true":
            print("\n❌ [오류] GitHub Actions 환경에서는 브라우저 창을 띄울 수 없습니다.")
            print("👉 GitHub 저장소의 [Settings] -> [Secrets and variables] -> [Actions] 에서")
            print("   'BRUNCH_COOKIE' Secret을 추가해주세요.\n")
            sys.exit(1)

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

    day_code = normalize_day(args.day)
    order_code = normalize_order(args.order)

    print(f"\n[1/3] '{day_code}' 요일 연재 글 목록을 불러옵니다 (정렬: {order_code})...")
    articles = fetch_serial_articles(day=day_code, order=order_code, max_count=max_count)
    if not articles:
        print("[!] 해당 요일에 올라온 연재 글이 없습니다.")
        if bot:
            bot.close()
        return

    interval_desc = f"{args.interval}초 (고정)" if args.interval is not None else f"{args.min_interval}~{args.max_interval}초 (랜덤)"
    print(f"[2/3] 총 {len(articles)}개의 연재 글을 가져왔습니다.")
    print(f"[3/3] {interval_desc} 간격으로 자동 좋아요를 시작합니다 (우측 상단 하트 기준). 중단: Ctrl+C\n")

    def log_cb(msg, level):
        now = time.strftime("%H:%M:%S")
        print(f"[{now}] [{level}] {msg}")

    def on_finish(success, skipped, failed):
        summary_path = os.getenv("GITHUB_STEP_SUMMARY")
        if summary_path:
            try:
                with open(summary_path, "a", encoding="utf-8") as f:
                    f.write("## ✨ 브런치 연재글 자동 좋아요 완료 리포트\n\n")
                    f.write(f"- **대상 요일**: `{day_code}`\n")
                    f.write(f"- **정렬 기준**: `{order_code}`\n")
                    f.write(f"- **간격**: `{interval_desc}`\n")
                    f.write(f"- **성공**: `{success}건` ✅\n")
                    f.write(f"- **스킵 (이미 좋아요됨)**: `{skipped}건` ℹ️\n")
                    f.write(f"- **실패**: `{failed}건` ❌\n\n")
                    f.write("| # | 글 제목 | 작가 | 처리 상태 |\n")
                    f.write("|---|---|---|---|\n")
                    for i, art in enumerate(articles):
                        st_name = art.get("status", "-")
                        icon = "✅" if st_name == "좋아요 완료" else ("ℹ️" if "이미" in st_name else "⚠️")
                        f.write(f"| {i+1} | [{art['article_title']}]({art['url']}) | {art['user_name']} | {icon} {st_name} |\n")
            except Exception as e:
                print(f"[Summary Write Error] {e}")

    scheduler = LikeScheduler(
        articles=articles,
        interval_min=args.min_interval,
        interval_max=args.max_interval,
        interval_seconds=args.interval,
        bot=bot,
        cookies=cookie_str if cookie_str else None,
        log_callback=log_cb,
        on_finish_callback=on_finish
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
