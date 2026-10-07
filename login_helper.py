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
    """쿠키 검증 후 파일에 저장 (사용자 수동 입력 차단 방지)"""
    cookie_str = cookie_str.strip()
    if not cookie_str:
        print("❌ 입력된 쿠키가 없습니다.")
        return False

    # 1. 파일에 우선 즉시 저장
    try:
        with open(COOKIE_FILE, "w", encoding="utf-8") as f:
            f.write(cookie_str)
    except Exception as e:
        print(f"❌ 파일 저장 실패: {e}")
        return False

    # 2. 세션 검증 시도
    is_ok, user = check_user_session(cookie_str)
    print("\n" + "=" * 65)
    if is_ok:
        print(f"  ✨ [인증 성공] '{user}' 작가님 계정으로 확인되었습니다!")
    else:
        print(f"  💾 쿠키 저장 완료 (세션 확인 응답: {user})")
    print(f"  📁 저장 경로: {COOKIE_FILE}")
    print("=" * 65)
    print("\n🎉 쿠키 저장이 완료되었습니다!")
    print("   매일 아침 06:00에 이 저장된 쿠키를 이용해 자동으로 좋아요가 실행됩니다.")
    print("   (PC를 켜두시면 스스로 작동하며, 창은 닫으셔도 됩니다.)\n")
    return True


def interactive_browser_login():
    """크롬 브라우저를 띄워 카카오 로그인 유도 후 세션 추출"""
    print("\n[1/3] 브런치 로그인 전용 크롬 창을 띄웁니다. 잠시만 기다려주세요...")
    bot = None
    try:
        bot = BrunchBot(browser_type="chrome", profile_dir=PROFILE_DIR)
        driver = bot.init_driver(headless=False)
        driver.get("https://brunch.co.kr")
    except Exception as e:
        print(f"❌ 브라우저 실행 실패: {e}")
        print("👉 대신 메뉴 2번(쿠키 직접 붙여넣기)을 이용해주세요.")
        return

    print("\n[2/3] 브라우저 창이 열렸습니다!")
    print("      👉 브런치 화면 우측 상단의 [시작하기] 또는 [로그인]을 눌러")
    print("         카카오 계정으로 로그인을 '완료'해주세요.")
    print("         (로그인 완료 후 프로필 사진이 보이면 성공입니다)")
    print("\n-----------------------------------------------------------")

    while True:
        try:
            input("👉 카카오 로그인을 끝마치신 후, 이 콘솔 창에서 [Enter]를 누르세요: ")
        except Exception:
            pass

        print("\n[3/3] 브라우저 세션에서 쿠키를 추출하고 인증을 검증합니다...")
        try:
            cur_url = driver.current_url
            if "accounts.kakao.com" in cur_url:
                print("⚠️ 현재 브라우저가 아직 카카오 계정 로그인 화면에 머물러 있습니다.")
                print("   👉 브라우저 창에서 카카오 아이디/비밀번호 입력 및 인증을 끝까지 완료해주세요!")
                retry = input("\n다시 확인하시겠습니까? (Y/n) [기본: Y]: ").strip().lower()
                if retry == "n":
                    break
                continue

            # 브런치 페이지로 새로고침/동기화
            if "brunch.co.kr" not in cur_url:
                driver.get("https://brunch.co.kr")
                time.sleep(1.5)

            # 브라우저 DOM 내 로그인 사용자 정보 확인
            dom_user = driver.execute_script("""
                try {
                    if (typeof B !== 'undefined' && B.User && (B.User.name || B.User.userId || B.User.profileId)) {
                        return B.User.name || B.User.nickname || B.User.userId;
                    }
                    const profile = document.querySelector('.btn_profile, .img_thumb, [data-tiara-layer*="profile"]');
                    if (profile && !document.querySelector('.wrap_side_profile.logout')) {
                        return '인증된 작가';
                    }
                } catch(e) {}
                return null;
            """)

            cookies = driver.get_cookies()
            cookie_parts = [f"{c['name']}={c['value']}" for c in cookies]
            cookie_str = "; ".join(cookie_parts)

            is_ok, user = check_user_session(cookie_str)
            user_display = dom_user or user

            if is_ok or dom_user:
                with open(COOKIE_FILE, "w", encoding="utf-8") as f:
                    f.write(cookie_str)
                print("\n" + "=" * 65)
                print(f"  ✨ [인증 성공] '{user_display}' 작가님 계정으로 확인되었습니다!")
                print(f"  💾 쿠키 저장 완료: {COOKIE_FILE}")
                print("=" * 65)
                print("\n🎉 모든 셋팅이 완료되었습니다!")
                print("   매일 아침 06:00에 이 저장된 쿠키를 이용해 자동으로 좋아요가 실행됩니다.")
                print("   (PC를 켜두시면 스스로 작동하며, 창은 닫으셔도 됩니다.)\n")
                break
            else:
                print("\n❌ [인증 실패] 브런치 로그인 정보를 찾을 수 없습니다.")
                print("   👉 브라우저 우측 상단에 [시작하기] 대신 '내 프로필 사진'이 보이는지 확인해주세요.")
                retry = input("다시 시도하시겠습니까? (Y/n) [기본: Y]: ").strip().lower()
                if retry == "n":
                    break
        except Exception as e:
            print(f"❌ 쿠키 추출 중 오류 발생: {e}")
            break

    if bot:
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

    try:
        choice = input("\n선택 번호 (1/2/3) [기본: 1]: ").strip()
    except (EOFError, KeyboardInterrupt):
        return

    if choice == "2":
        direct_cookie_input()
    elif choice == "3":
        print("종료합니다.")
        return
    else:
        interactive_browser_login()

    try:
        input("\n계속하려면 아무 키나 누르십시오 . . .")
    except (EOFError, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    main()
