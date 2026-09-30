"""
Browser Bot Module for Brunch Automation
셀레니움을 활용하여 브런치 로그인 및 자동 좋아요(Like)를 수행하는 봇 모듈
"""

import os
import time
import random
import threading
from typing import Optional, Tuple, Callable

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions


class BrunchBot:
    def __init__(self, browser_type: str = "chrome", profile_dir: Optional[str] = None):
        """
        :param browser_type: 'chrome' 또는 'edge'
        :param profile_dir: 브라우저 프로필 저장 경로 (지정하지 않으면 기본 경로 사용)
        """
        self.browser_type = browser_type.lower()
        if not profile_dir:
            # 실행 경로 기준 brunch_profile 폴더 생성
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.profile_dir = os.path.join(base_dir, "brunch_profile")
        else:
            self.profile_dir = os.path.abspath(profile_dir)

        os.makedirs(self.profile_dir, exist_ok=True)
        self.driver: Optional[webdriver.Remote] = None
        self._is_stopped = False
        self._is_paused = False

    def init_driver(self, headless: bool = False) -> webdriver.Remote:
        """웹드라이버를 초기화합니다 (프로필 세션 유지)."""
        if self.driver:
            try:
                # 드라이버가 살아있는지 체크
                _ = self.driver.title
                return self.driver
            except Exception:
                self.close()

        # 크롬/엣지 비정상 종료 시 남아있을 수 있는 SingletonLock 정리
        lock_file = os.path.join(self.profile_dir, "SingletonLock")
        if os.path.exists(lock_file):
            try:
                os.remove(lock_file)
            except Exception:
                pass

        if self.browser_type == "edge":
            options = EdgeOptions()
            options.add_argument(f"--user-data-dir={self.profile_dir}")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--start-maximized")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--remote-debugging-port=0")
            if headless:
                options.add_argument("--headless=new")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            try:
                self.driver = webdriver.Edge(options=options)
            except Exception:
                # Edge 실패 시 기본 프로필로 재시도
                options_fallback = EdgeOptions()
                if headless:
                    options_fallback.add_argument("--headless=new")
                self.driver = webdriver.Edge(options=options_fallback)
        else:
            options = ChromeOptions()
            options.add_argument(f"--user-data-dir={self.profile_dir}")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--start-maximized")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--remote-debugging-port=0")
            if headless:
                options.add_argument("--headless=new")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            try:
                self.driver = webdriver.Chrome(options=options)
            except Exception:
                # 크롬 프로필 잠김 등 실패 시 기본 옵션 또는 Edge로 안전하게 대체
                try:
                    options_fallback = ChromeOptions()
                    if headless:
                        options_fallback.add_argument("--headless=new")
                    self.driver = webdriver.Chrome(options=options_fallback)
                except Exception:
                    options_edge = EdgeOptions()
                    if headless:
                        options_edge.add_argument("--headless=new")
                    self.driver = webdriver.Edge(options=options_edge)

        # navigator.webdriver 탐지 우회
        try:
            self.driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """
                }
            )
        except Exception:
            pass

        return self.driver

    def check_login_status(self) -> bool:
        """현재 브라우저 세션이 브런치에 로그인되어 있는지 확인합니다."""
        if not self.driver:
            self.init_driver(headless=True)

        try:
            self.driver.get("https://brunch.co.kr")
            time.sleep(2)
            # 쿠키 확인: b_uid 또는 brunch_session
            cookies = {c["name"]: c["value"] for c in self.driver.get_cookies()}
            if "b_uid" in cookies or "brunch_session" in cookies:
                return True

            # DOM 확인: 로그인 버튼 대신 프로필/글쓰기/메뉴가 있는지 체크
            login_buttons = self.driver.find_elements(
                By.XPATH, "//button[contains(text(), '시작하기') or contains(text(), '로그인')]"
            )
            # 시작하기 버튼이 없거나 프로필 메뉴가 나타나면 로그인 상태
            user_elements = self.driver.find_elements(
                By.CSS_SELECTOR, ".img_thumb, .btn_profile, [data-tiara-layer*='profile'], .wrap_profile"
            )
            return len(user_elements) > 0 and len(login_buttons) == 0
        except Exception as e:
            print(f"[Bot] 로그인 상태 체크 오류: {e}")
            return False

    def open_login_window(self, on_login_success: Optional[Callable] = None):
        """
        사용자가 카카오 로그인을 직접 수행할 수 있도록 브라우저를 엽니다.
        로그인이 완료될 때까지 대기하고 감지합니다.
        """
        # 로그인 창은 반드시 화면에 보여야 하므로 headless=False
        driver = self.init_driver(headless=False)
        driver.get("https://brunch.co.kr")

        # 로그인 시작 버튼 클릭 유도 또는 로그인 페이지 이동
        time.sleep(1.5)
        try:
            # 시작하기 / 로그인 버튼 탐색 후 클릭 시도
            start_btn = driver.find_elements(
                By.XPATH, "//button[contains(., '시작하기') or contains(., '로그인')]"
            )
            if start_btn:
                start_btn[0].click()
        except Exception:
            pass

        # 백그라운드 모니터링
        def monitor():
            while not self._is_stopped:
                time.sleep(2)
                try:
                    cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
                    if "b_uid" in cookies or "brunch_session" in cookies:
                        print("[Bot] 로그인 성공 감지!")
                        if on_login_success:
                            on_login_success()
                        break
                except Exception:
                    break

        t = threading.Thread(target=monitor, daemon=True)
        t.start()

    def like_article(self, url: str) -> Tuple[str, str]:
        """
        특정 글 페이지에 접속하여 '우측 상단 하트(라이킷)' 버튼을 누릅니다.
        (위치 변동 시에도 화면 상단/GNB의 하트 아이콘을 정확히 찾아 클릭)
        
        :return: (결과 코드, 메시지)
                 - 'LIKED': 좋아요 성공
                 - 'ALREADY_LIKED': 이미 좋아요가 눌러진 글
                 - 'NOT_LOGGED_IN': 로그인이 필요함
                 - 'ERROR': 오류 발생
        """
        if not self.driver:
            self.init_driver(headless=False)

        try:
            self.driver.get(url)
            # 페이지 로딩 대기
            time.sleep(random.uniform(1.8, 2.5))

            # 1. 페이지 내 LIKE_DATA 전역 상태 우선 확인 (이미 좋아요 여부)
            try:
                like_data_str = self.driver.execute_script(
                    "return document.getElementById('LIKE_DATA')?.textContent || '';"
                )
                if like_data_str and '"isLiked":true' in like_data_str.replace(" ", ""):
                    return "ALREADY_LIKED", "이미 좋아요가 눌러진 글입니다 (LIKE_DATA 확인)."
            except Exception:
                pass

            heart_btn = None
            is_already_liked = False

            # 2. 우측 상단 GNB 하트 버튼 우선 탐색
            # 브런치 상단 GNB의 하트 버튼:
            # <button class="wrap_icon"><span class="ico_view_cover ico_likeit_like">라이킷</span><span class="text_cnt">12</span></button>
            # (좋아요 완료 시: span class에 ico_likeit_unlike 포함)
            try:
                heart_spans = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    "span.ico_likeit_like, span.ico_likeit_unlike, .ico_likeit_like, .ico_likeit_unlike"
                )
                for span in heart_spans:
                    try:
                        btn = span.find_element(By.XPATH, "./ancestor::button")
                        loc = btn.location
                        # 화면 상단 영역 (y < 350) 우선 타겟팅
                        if loc.get("y", 0) < 350:
                            heart_btn = btn
                            span_cls = span.get_attribute("class") or ""
                            if "ico_likeit_unlike" in span_cls:
                                is_already_liked = True
                            break
                    except Exception:
                        continue
            except Exception:
                pass

            # 3. 대체 탐색 (상단 정렬 기준)
            if not heart_btn:
                candidates = self.driver.find_elements(
                    By.XPATH,
                    "//button[.//span[contains(text(), '라이킷')] or contains(@aria-label, '라이킷') or contains(@class, 'btn_like')]"
                )
                if candidates:
                    # y좌표가 가장 작은 상단 버튼 우선 선택 (우측 상단)
                    candidates.sort(key=lambda b: (b.location.get("y", 9999), -b.location.get("x", 0)))
                    heart_btn = candidates[0]
                    btn_html = heart_btn.get_attribute("outerHTML") or ""
                    custom_attr = heart_btn.get_attribute("data-tiara-custom") or ""
                    if "ico_likeit_unlike" in btn_html or "liketype=dislike" in custom_attr or "text-[#00c6be]" in btn_html:
                        is_already_liked = True

            if not heart_btn:
                return "ERROR", "우측 상단 하트(라이킷) 버튼을 찾을 수 없습니다."

            # 이미 좋아요 상태라면 클릭 생략
            if is_already_liked:
                return "ALREADY_LIKED", "우측 상단 하트 확인: 이미 좋아요가 눌러진 글입니다 (스킵)."

            # 하트 버튼을 화면에 가볍게 맞추기
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'nearest'});", heart_btn)
                time.sleep(0.3)
            except Exception:
                pass

            # 클릭 시도
            try:
                heart_btn.click()
            except Exception:
                # JavaScript 직접 클릭
                self.driver.execute_script("arguments[0].click();", heart_btn)

            time.sleep(1.2)

            # 로그인 필요 모달이 떴는지 확인
            login_modal = self.driver.find_elements(
                By.CSS_SELECTOR, ".wrap_login_modal, .layer_login, #loginModal"
            )
            if login_modal and any(m.is_displayed() for m in login_modal):
                return "NOT_LOGGED_IN", "로그인이 필요합니다. 먼저 카카오 로그인을 진행해주세요."

            # 클릭 후 아이콘 변경 확인
            try:
                new_html = heart_btn.get_attribute("outerHTML") or ""
                custom_attr = heart_btn.get_attribute("data-tiara-custom") or ""
                if "ico_likeit_unlike" in new_html or "liketype=dislike" in custom_attr:
                    return "LIKED", "우측 상단 하트 좋아요 성공!"
            except Exception:
                pass

            return "LIKED", "우측 상단 하트 좋아요 클릭 완료."

        except Exception as e:
            return "ERROR", f"실행 중 오류 발생: {str(e)}"

    def close(self):
        """브라우저 종료"""
        self._is_stopped = True
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
