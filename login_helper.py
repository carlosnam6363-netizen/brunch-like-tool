"""
Brunch Login Helper (브런치 카카오 로그인 도우미)
- 브라우저 창을 띄워 사용자가 카카오 로그인을 직접 수행할 수 있도록 지원
- 로그인 완료 후 Enter를 누르면 쿠키를 즉시 추출하여 brunch_profile/last_cookie.txt에 영구 저장
- 또는 이미 복사해둔 쿠키를 직접 붙여넣는 기능도 함께 제공
"""
import os
import sys
import time

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from browser_bot import BrunchBot
from brunch_api import check_user_session

PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brunch_profile")
os.makedirs(PROFILE_DIR, exist_ok=True)
COOKIE_FILE = os.path.join(PROFILE_DIR, "last_cookie.txt")


def save_and_verify(cookie_str: str) -> bool:
    """쿠키 검증 후 파일에 저장"""
    cookie_str = cookie_str.strip()
    if not cookie_str:
        print("❌ 입력된 쿠키가 없습니다.")
        return False

    is_ok, user = check_user_session(cookie_str)
    # 파일 저장
    try:
        with open(COOKIE_FILE, "w", encoding="utf-8") as f:
            f.write(cookie_str)
    except Exception as e:
        print(f"❌ 파일 저장 실패: {e}")
        return False

    print("\n" + "=" * 65)
    if is_ok:
        print(f"  ✨ [인증 성공] '{user}' 작가님 계정으로 확인되었습니다!")
    else:
        print(f"  ⚠️ [세션 안내] 검증 응답: {user}")
    print(f"  💾 쿠키 저장 완료: {COOKIE_FILE}")
    print("=" * 65)
    print("\n🎉 모든 셋팅이 완료되었습니다!")
    print("   내일 아침 08:00에 이 저장된 쿠키를 이용해 자동으로 좋아요가 실행됩니다.")
    print("   (PC를 켜두시면 스스로 작동하며, 창은 닫으셔도 됩니다.)\n")
    return True


def interactive_browser_login():
    """크롬 브라우저를 띄워 카카오 로그인 유도 후 세션 추출"""
    print("\n[1/3] 브런치 로그인 전용 크롬 창을 띄웁니다. 잠시만 기다려주세요...")
    try:
        bot = BrunchBot(browser_type="chrome", profile_dir=PROFILE_DIR)
        driver = bot.init_driver(headless=False)
        driver.get("https://brunch.co.kr")
    except Exception as e:
        print(f"❌ 브라우저 실행 실패: {e}")
        print("👉 대신 메뉴 2번(쿠키 직접 붙여넣기)을 이용해주세요.")
        return

    print("\n[2/3] 브라우저 창이 열렸습니다!")
    print("      👉 브런치 화면에서 [시작하기] 또는 [로그인]을 눌러")
    print("         카카오 계정으로 로그인을 완료해주세요.")
    print("\n-----------------------------------------------------------")
    print(" 로그인을 완료하신 후, 이 콘솔 창으로 돌아와 [Enter] 키를 누르세요.")
    print("-----------------------------------------------------------")

    try:
        input("\n[Enter] 키를 누르면 로그인을 확인하고 쿠키를 자동 저장합니다: ")
    except Exception:
        pass

    print("\n[3/3] 브라우저 세션에서 쿠키를 추출하고 인증을 검증합니다...")
    try:
        driver.get("https://brunch.co.kr")
        time.sleep(1.5)
        cookies = driver.get_cookies()
        cookie_parts = [f"{c['name']}={c['value']}" for c in cookies]
        cookie_str = "; ".join(cookie_parts)

        save_and_verify(cookie_str)
    except Exception as e:
        print(f"❌ 쿠키 추출 중 오류 발생: {e}")
    finally:
        bot.close()
        print("브라우저 창을 정리했습니다.")


def direct_cookie_input():
    """복사한 쿠키를 직접 붙여넣어 저장"""
    print("\n-----------------------------------------------------------")
    print(" 브런치(brunch.co.kr)에 로그인된 상태에서 복사한 쿠키 문자열을")
    print(" 아래에 마우스 우클릭 또는 Ctrl+V로 붙여넣고 [Enter]를 누르세요.")
    print("-----------------------------------------------------------")
    try:
        cookie_str = input("\n쿠키 붙여넣기: ").strip()
        save_and_verify(cookie_str)
    except Exception as e:
        print(f"입력 오류: {e}")


def main():
    print("=" * 65)
    print(" 🔑 브런치 자동 좋아요 - 카카오 로그인 및 쿠키 등록 도우미")
    print("=" * 65)
    print("\n원하시는 로그인 등록 방식을 선택해주세요:")
    print("  1. 브라우저 창을 띄워 카카오 로그인하기 (추천)")
    print("  2. 이미 복사해둔 쿠키 문자열 직접 붙여넣기")
    print("  3. 종료")

    choice = input("\n선택 번호 (1/2/3) [기본: 1]: ").strip()
    if choice == "2":
        direct_cookie_input()
    elif choice == "3":
        print("종료합니다.")
    else:
        interactive_browser_login()

    input("\n계속하려면 아무 키나 누르십시오 . . .")


if __name__ == "__main__":
    main()
