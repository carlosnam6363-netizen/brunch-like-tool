"""
Browser Bot Module for Brunch Automation
셀레니움을 활용하여 브런치 로그인 및 자동 좋아요(Like)를 수행하는 봇 모듈
- 우측 상단 GNB 하트 버튼 정밀 타겟팅 및 클릭
- Chrome / Edge 브라우저 및 프로필 세션 재사용 지원
- 불필요한 대기 및 중복 코드 제거로 속도 및 안정성 최적화
"""

import os
import time
import random
import threading
from typing import Optional, Tuple, Callable

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
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
        """Chrome / Edge 공통 브라우저 옵션을 생성합니다. (고정 1920x1080 및 자동화 플래그 회피)"""
        OptionsClass = EdgeOptions if browser_type == "edge" else ChromeOptions
        options = OptionsClass()
        if use_profile:
            options.add_argument(f"--user-data-dir={self.profile_dir}")
        options.add_argument("--disable-blink-features=AutomationControlled")
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

        # 1. 자연스러운 비정형 해상도 및 창 위치 동적 배정 (고정 1920x1080 지문 회피)
        try:
            w = random.randint(1240, 1380)
            h = random.randint(820, 940)
            pos_x = random.randint(30, 100)
            pos_y = random.randint(25, 75)
            self.driver.set_window_size(w, h)
            self.driver.set_window_position(pos_x, pos_y)
        except Exception:
            pass

        # 2. navigator.webdriver 및 브라우저 지문(Fingerprint) 정밀 은폐 스크립트 주입
        stealth_js = """
        // (1) navigator.webdriver 플래그 숨기기
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });

        // (2) window.chrome 런타임 객체 흉내내기
        if (!window.chrome) {
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
        }

        // (3) navigator.plugins 정상 브라우저처럼 보이도록 모사
        if (!navigator.plugins || navigator.plugins.length === 0) {
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        }

        // (4) navigator.languages 한국어 표준 로케일 주입
        Object.defineProperty(navigator, 'languages', {
            get: () => ['ko-KR', 'ko', 'en-US', 'en']
        });
        """
        try:
            self.driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": stealth_js}
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

    def simulate_human_reading_and_scroll(self, min_read_sec: float = 3.0, max_read_sec: float = 12.0):
        """
        정교한 사람다운 글 읽기 및 스크롤 행동 모사:
        - 300~700px 단위의 가속도 스크롤
        - 20~25% 확률의 100~200px 역스크롤(Back-scroll, 다시 읽기 모사)
        - 글 길이에 비례한 체류 시간 동적 계산
        """
        if not self.driver:
            return

        try:
            # 1. 본문 글자 수 및 총 스크롤 높이 측정
            body_info = self.driver.execute_script("""
                const bodyEl = document.querySelector('.wrap_body, .article_body, .wrap_article_body, body');
                return {
                    charCount: bodyEl ? (bodyEl.innerText || '').length : 1000,
                    scrollHeight: Math.max(
                        document.body.scrollHeight || 0,
                        document.documentElement.scrollHeight || 0,
                        1500
                    )
                };
            """)
            char_count = body_info.get("charCount", 1000)
            scroll_height = body_info.get("scrollHeight", 2000)

            # 공백 포함 1,000자당 약 3.5~6초 체류 (최소 min_read_sec초 ~ 최대 max_read_sec초로 캡핑)
            target_time = max(min_read_sec, min(max_read_sec, (char_count / 1000.0) * random.uniform(3.5, 6.0)))

            start_t = time.time()
            cur_scroll = 0

            while (time.time() - start_t < target_time) and not self._is_stopped:
                # 80% 확률로 아래로 300~700px 스크롤, 20% 확률로 위로 100~200px 역스크롤
                if cur_scroll > 400 and random.random() < 0.22:
                    # 역스크롤 (재독 모사)
                    back_px = random.randint(120, 220)
                    cur_scroll = max(0, cur_scroll - back_px)
                    self.driver.execute_script(f"window.scrollBy({{top: -{back_px}, behavior: 'smooth'}});")
                else:
                    # 아래로 읽기 스크롤
                    down_px = random.randint(320, 680)
                    cur_scroll += down_px
                    self.driver.execute_script(f"window.scrollBy({{top: {down_px}, behavior: 'smooth'}});")

                # 읽는 중 자연스러운 정규분포 지연 (0.6초 ~ 1.5초)
                pause = max(0.4, random.gauss(0.9, 0.25))
                time.sleep(pause)

                if cur_scroll >= scroll_height:
                    break

            # 스크롤 후 상단 라이킷 버튼 위치로 부드럽게 복귀
            self.driver.execute_script("window.scrollTo({top: 0, behavior: 'smooth'});")
            time.sleep(random.uniform(0.4, 0.8))
        except Exception:
            pass

    def like_article(self, url: str) -> Tuple[str, str]:
        """
        특정 글 페이지에 접속하여 본문 읽기/스크롤 행동 모사 후 '우측 상단 하트(라이킷)' 버튼을 누릅니다.
        
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

            # 1. LIKE_DATA 전역 스크립트 상태 즉시 확인 (이미 좋아요된 글은 불필요한 대기 없이 즉시 반환)
            try:
                is_liked = self.driver.execute_script("""
                    const data = document.getElementById('LIKE_DATA')?.textContent;
                    if (data) {
                        try { return JSON.parse(data).isLiked === true; } catch(e) {}
                    }
                    return null;
                """)
                if is_liked is True:
                    return "ALREADY_LIKED", "이미 좋아요가 눌러진 글입니다 (LIKE_DATA 즉시 확인)."
            except Exception:
                pass

            # 2. 미좋아요 글일 때만 인간다운 본문 읽기 및 스크롤 시뮬레이션 수행
            self.simulate_human_reading_and_scroll()

            heart_btn = None
            is_already_liked = False

            # 3. 우측 상단 GNB 하트 버튼 정밀 탐색 (y < 350 상단 영역)
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

            # 4. 대체 탐색 (상단 우측 기준)
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

            # 5. 인간다운 마우스 호버(Hover) 후 클릭 수행
            try:
                actions = ActionChains(self.driver)
                actions.move_to_element(heart_btn).perform()
                # 클릭 직전 0.25~0.55초의 자연스러운 멈춤
                time.sleep(random.uniform(0.25, 0.55))
                actions.click().perform()
            except Exception:
                time.sleep(random.uniform(0.2, 0.4))
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
