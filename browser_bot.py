"""
Browser Bot Module for Brunch Automation
셀레니움을 활용하여 브런치 로그인 및 자동 좋아요(Like)를 수행하는 봇 모듈
- 우측 상단 GNB 하트 버튼 정밀 타겟팅 및 클릭
- Chrome / Edge 브라우저 및 프로필 세션 재사용 지원
- 불필요한 대기 및 중복 코드 제거로 속도 및 안정성 최적화
"""

import os
import time
import threading
from typing import Optional, Tuple, Callable

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions


class BrunchBot:
    def __init__(self, browser_type: str = "chrome", profile_dir: Optional[str] = None):
        """
        :param browser_type: 'chrome' 또는 'edge'
        :param profile_dir: 브라우저 프로필 저장 경로 (미지정 시 brunch_profile 기본 폴더)
        """
        self.browser_type = browser_type.lower()
        if not profile_dir:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.profile_dir = os.path.join(base_dir, "brunch_profile")
        else:
            self.profile_dir = os.path.abspath(profile_dir)

        os.makedirs(self.profile_dir, exist_ok=True)
        self.driver: Optional[webdriver.Remote] = None
        self._is_stopped = False

    def _create_options(self, browser_type: str, use_profile: bool = True, headless: bool = False):
        """Chrome / Edge 공통 브라우저 옵션을 생성합니다."""
        OptionsClass = EdgeOptions if browser_type == "edge" else ChromeOptions
        options = OptionsClass()
        if use_profile:
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
        return options

    def _create_driver_instance(self, browser_type: str, headless: bool) -> webdriver.Remote:
        """드라이버 객체를 생성하며, 프로필 잠금 시 안전하게 폴백합니다."""
        DriverClass = webdriver.Edge if browser_type == "edge" else webdriver.Chrome
        try:
            return DriverClass(options=self._create_options(browser_type, use_profile=True, headless=headless))
        except Exception:
            return DriverClass(options=self._create_options(browser_type, use_profile=False, headless=headless))

    def init_driver(self, headless: bool = False) -> webdriver.Remote:
        """웹드라이버를 초기화합니다 (프로필 세션 유지)."""
        if self.driver:
            try:
                _ = self.driver.title
                return self.driver
            except Exception:
                self.close()

        # 브라우저 비정상 종료 시 남아있을 수 있는 SingletonLock 정리
        lock_file = os.path.join(self.profile_dir, "SingletonLock")
        if os.path.exists(lock_file):
            try:
                os.remove(lock_file)
            except Exception:
                pass

        try:
            self.driver = self._create_driver_instance(self.browser_type, headless)
        except Exception:
            # 주 브라우저 실패 시 대체 브라우저 시도
            fallback_type = "chrome" if self.browser_type == "edge" else "edge"
            self.driver = self._create_driver_instance(fallback_type, headless)

        # navigator.webdriver 탐지 우회
        try:
            self.driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
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
            time.sleep(1.5)
            cookies = {c["name"]: c["value"] for c in self.driver.get_cookies()}
            if "b_uid" in cookies or "brunch_session" in cookies:
                return True

            login_buttons = self.driver.find_elements(
                By.XPATH, "//button[contains(text(), '시작하기') or contains(text(), '로그인')]"
            )
            user_elements = self.driver.find_elements(
                By.CSS_SELECTOR, ".img_thumb, .btn_profile, [data-tiara-layer*='profile'], .wrap_profile"
            )
            return len(user_elements) > 0 and len(login_buttons) == 0
        except Exception as e:
            print(f"[Bot] 로그인 상태 체크 오류: {e}")
            return False

    def open_login_window(self, on_login_success: Optional[Callable] = None):
        """
        사용자가 카카오 로그인을 직접 수행할 수 있도록 브라우저를 열고 로그인 완료를 감지합니다.
        """
        driver = self.init_driver(headless=False)
        driver.get("https://brunch.co.kr")

        time.sleep(1.2)
        try:
            start_btn = driver.find_elements(
                By.XPATH, "//button[contains(., '시작하기') or contains(., '로그인')]"
            )
            if start_btn:
                start_btn[0].click()
        except Exception:
            pass

        def monitor():
            while not self._is_stopped:
                time.sleep(2)
                try:
                    cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
                    if "b_uid" in cookies or "brunch_session" in cookies:
                        if on_login_success:
                            on_login_success()
                        break
                except Exception:
                    break

        threading.Thread(target=monitor, daemon=True).start()

    def like_article(self, url: str) -> Tuple[str, str]:
        """
        특정 글 페이지에 접속하여 '우측 상단 하트(라이킷)' 버튼을 누릅니다.
        
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
            time.sleep(1.5)

            # 1. LIKE_DATA 전역 스크립트 상태 확인 (초고속 판단)
            try:
                is_liked = self.driver.execute_script("""
                    const data = document.getElementById('LIKE_DATA')?.textContent;
                    if (data) {
                        try { return JSON.parse(data).isLiked === true; } catch(e) {}
                    }
                    return false;
                """)
                if is_liked:
                    return "ALREADY_LIKED", "이미 좋아요가 눌러진 글입니다 (LIKE_DATA 확인)."
            except Exception:
                pass

            heart_btn = None
            is_already_liked = False

            # 2. 우측 상단 GNB 하트 버튼 정밀 탐색 (y < 350 상단 영역)
            try:
                heart_spans = self.driver.find_elements(
                    By.CSS_SELECTOR, "span.ico_likeit_like, span.ico_likeit_unlike"
                )
                for span in heart_spans:
                    try:
                        btn = span.find_element(By.XPATH, "./ancestor::button")
                        if btn.location.get("y", 999) < 350:
                            heart_btn = btn
                            if "ico_likeit_unlike" in (span.get_attribute("class") or ""):
                                is_already_liked = True
                            break
                    except Exception:
                        continue
            except Exception:
                pass

            # 3. 대체 탐색 (상단 우측 기준)
            if not heart_btn:
                candidates = self.driver.find_elements(
                    By.XPATH,
                    "//button[.//span[contains(text(), '라이킷')] or contains(@aria-label, '라이킷')]"
                )
                if candidates:
                    candidates.sort(key=lambda b: (b.location.get("y", 9999), -b.location.get("x", 0)))
                    heart_btn = candidates[0]
                    html_content = heart_btn.get_attribute("outerHTML") or ""
                    custom_attr = heart_btn.get_attribute("data-tiara-custom") or ""
                    if "ico_likeit_unlike" in html_content or "liketype=dislike" in custom_attr:
                        is_already_liked = True

            if not heart_btn:
                return "ERROR", "우측 상단 하트(라이킷) 버튼을 찾을 수 없습니다."

            if is_already_liked:
                return "ALREADY_LIKED", "이미 좋아요가 눌러진 글입니다 (스킵)."

            # 4. 클릭 수행
            try:
                heart_btn.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", heart_btn)

            time.sleep(1.0)

            # 로그인 필요 모달 발생 여부 확인
            login_modal = self.driver.find_elements(By.CSS_SELECTOR, ".wrap_login_modal, .layer_login, #loginModal")
            if login_modal and any(m.is_displayed() for m in login_modal):
                return "NOT_LOGGED_IN", "로그인이 필요합니다. 먼저 카카오 로그인을 진행해주세요."

            return "LIKED", "우측 상단 하트 좋아요 완료"

        except Exception as e:
            return "ERROR", f"실행 중 오류 발생: {str(e)}"

    def close(self):
        """브라우저 종료 및 리소스 정리"""
        self._is_stopped = True
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
