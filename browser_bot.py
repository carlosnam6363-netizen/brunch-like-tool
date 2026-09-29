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

        if self.browser_type == "edge":
            options = EdgeOptions()
            options.add_argument(f"--user-data-dir={self.profile_dir}")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--start-maximized")
            if headless:
                options.add_argument("--headless=new")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            self.driver = webdriver.Edge(options=options)
        else:
            options = ChromeOptions()
            options.add_argument(f"--user-data-dir={self.profile_dir}")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--start-maximized")
            if headless:
                options.add_argument("--headless=new")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            self.driver = webdriver.Chrome(options=options)

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
        특정 글 페이지에 접속하여 '좋아요(라이킷)' 버튼을 누릅니다.
        
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
            time.sleep(random.uniform(2.0, 3.0))

            # 본문 하단까지 부드럽게 스크롤 (자연스러운 사용자 모션)
            try:
                self.driver.execute_script(
                    "window.scrollTo({top: document.body.scrollHeight * 0.7, behavior: 'smooth'});"
                )
                time.sleep(1.0)
                self.driver.execute_script(
                    "window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'});"
                )
                time.sleep(1.5)
            except Exception:
                pass

            # 라이킷 버튼 찾기
            # 브런치의 라이킷 버튼은 class="btn_like" 이거나 aria-label="라이킷 버튼"
            wait = WebDriverWait(self.driver, 10)
            like_btn = None
            try:
                like_btn = wait.until(
                    EC.presence_of_element_located((
                        By.CSS_SELECTOR,
                        "button.btn_like, button[aria-label*='라이킷'], [data-tiara-action-kind='Like']"
                    ))
                )
            except Exception:
                # 대체 선택자
                btns = self.driver.find_elements(By.CSS_SELECTOR, "button.btn_like, button[aria-label*='라이킷']")
                if btns:
                    like_btn = btns[0]

            if not like_btn:
                return "ERROR", "라이킷(좋아요) 버튼을 찾을 수 없습니다."

            # 이미 좋아요 상태인지 확인
            # 브런치 웹페이지에서는 좋아요가 눌렸을 때 data-tiara-custom="liketype=dislike"가 됩니다.
            custom_attr = like_btn.get_attribute("data-tiara-custom") or ""
            outer_html = like_btn.get_attribute("outerHTML") or ""

            # 이미 좋아요인지 확인: liketype=dislike 또는 클래스 active 또는 특정 하트 채움
            if "liketype=dislike" in custom_attr or "text-[#00c6be]" in outer_html or "on" in like_btn.get_attribute("class").split():
                return "ALREADY_LIKED", "이미 좋아요가 눌러진 글입니다 (스킵)."

            # 버튼이 화면 중앙에 보이도록 스크롤
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", like_btn)
            time.sleep(0.5)

            # 클릭 시도
            try:
                like_btn.click()
            except Exception:
                # 일반 클릭 실패 시 JavaScript 클릭
                self.driver.execute_script("arguments[0].click();", like_btn)

            time.sleep(1.5)

            # 로그인 팝업이 떴는지 확인 (비로그인 상태일 때 모달 오픈됨)
            login_modal = self.driver.find_elements(
                By.CSS_SELECTOR, ".wrap_login_modal, .layer_login, #loginModal"
            )
            if login_modal and any(m.is_displayed() for m in login_modal):
                return "NOT_LOGGED_IN", "로그인이 필요합니다. 먼저 카카오 로그인을 진행해주세요."

            # 클릭 후 상태 변경 확인
            new_custom = like_btn.get_attribute("data-tiara-custom") or ""
            if "liketype=dislike" in new_custom:
                return "LIKED", "좋아요를 성공적으로 눌렀습니다."

            return "LIKED", "좋아요 클릭 완료."

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
