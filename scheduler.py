"""
Scheduler Module
글 목록 순회 및 랜덤 간격(1초~30초) 좋아요 처리 실행기
- 셀레니움 브라우저 모드와 순수 HTTP API(쿠키) 모드 양방향 지원
- 1초 ~ 30초 사이의 자연스러운 랜덤 지연 대기
- 실행 중/일시정지 중 실시간 간격 수정 즉시 반영
- 완료된 글 콜백 지원으로 중복 처리 원천 방지
- HTTP 세션 재사용으로 네트워크 통신 성능 최적화
"""

import time
import random
import threading
import requests
from typing import List, Dict, Callable, Optional, Tuple, Union
from brunch_api import like_article_api, parse_cookie_string


class LikeScheduler:
    def __init__(
        self,
        articles: List[Dict],
        interval_min: int = 1,
        interval_max: int = 30,
        interval_seconds: Optional[int] = None,
        bot=None,
        cookies: Optional[Union[str, dict]] = None,
        log_callback: Optional[Callable[[str, str], None]] = None,
        article_update_callback: Optional[Callable[[int, str], None]] = None,
        article_completed_callback: Optional[Callable[[Dict, str], None]] = None,
        countdown_callback: Optional[Callable[[int, int], None]] = None,
        on_finish_callback: Optional[Callable[[int, int, int], None]] = None,
        get_interval_callback: Optional[Callable[[], Tuple[int, int]]] = None
    ):
        """
        :param articles: 처리할 글 정보 리스트
        :param interval_min: 최소 대기 초 (기본: 1초)
        :param interval_max: 최대 대기 초 (기본: 30초)
        :param interval_seconds: 고정 간격 초 (전달 시 min=max 설정)
        :param bot: BrunchBot 인스턴스 (브라우저 모드)
        :param cookies: 브런치 쿠키 문자열 또는 dict (순수 API 모드)
        :param log_callback: 로그 출력 콜백 (message, level)
        :param article_update_callback: 글 상태 업데이트 콜백 (index, status)
        :param article_completed_callback: 글 완료(성공/스킵) 시 호출되는 콜백 (article, status)
        :param countdown_callback: 남은 초 콜백 (remaining_seconds, total_wait_seconds)
        :param on_finish_callback: 전체 완료 콜백 (success_count, skipped_count, failed_count)
        :param get_interval_callback: 실시간 간격 조회 콜백 (func -> (min, max))
        """
        self.articles = articles
        if interval_seconds is not None:
            self.interval_min = interval_seconds
            self.interval_max = interval_seconds
        else:
            self.interval_min = max(1, interval_min)
            self.interval_max = max(self.interval_min, interval_max)

        self.bot = bot
        self.cookies = parse_cookie_string(cookies) if cookies else None
        self.log_callback = log_callback or (lambda msg, lvl: print(f"[{lvl}] {msg}"))
        self.article_update_callback = article_update_callback
        self.article_completed_callback = article_completed_callback
        self.countdown_callback = countdown_callback
        self.on_finish_callback = on_finish_callback
        self.get_interval_callback = get_interval_callback

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()

        self._session: Optional[requests.Session] = None
        if self.cookies:
            self._session = requests.Session()
            self._session.cookies.update(self.cookies)

        self.success_count = 0
        self.skipped_count = 0
        self.failed_count = 0
        self.is_running = False

    def log(self, message: str, level: str = "INFO"):
        if self.log_callback:
            self.log_callback(message, level)

    def update_interval(self, min_sec: int, max_sec: int):
        """실행 중 또는 일시정지 중 좋아요 대기 간격을 실시간으로 갱신합니다."""
        old_min, old_max = self.interval_min, self.interval_max
        self.interval_min = max(1, min_sec)
        self.interval_max = max(self.interval_min, max_sec)
        if (old_min, old_max) != (self.interval_min, self.interval_max):
            self.log(f"⚡ 대기 간격이 {self.interval_min}~{self.interval_max}초로 실시간 갱신되었습니다.", "INFO")

    def start(self):
        """스케줄러 작업 시작 (백그라운드 스레드)"""
        if self.is_running:
            return

        self._stop_event.clear()
        self._pause_event.set()
        self.is_running = True
        self.success_count = 0
        self.skipped_count = 0
        self.failed_count = 0

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def pause(self):
        """일시 정지"""
        self._pause_event.clear()
        self.log("작업이 일시 정지되었습니다. 간격 숫자를 수정한 후 [재개]를 누르면 새 간격이 적용됩니다.", "WARN")

    def resume(self):
        """재개"""
        # 재개 시 최신 간격 조회 반영
        if self.get_interval_callback:
            try:
                new_min, new_max = self.get_interval_callback()
                self.update_interval(new_min, new_max)
            except Exception:
                pass
        self._pause_event.set()
        self.log(f"작업을 다시 시작합니다. (적용 간격: {self.interval_min}~{self.interval_max}초)", "INFO")

    def stop(self):
        """완전 중단"""
        self._stop_event.set()
        self._pause_event.set()
        self.is_running = False
        if self._session:
            try:
                self._session.close()
            except Exception:
                pass
            self._session = None
        self.log("작업 중단 요청이 접수되었습니다.", "WARN")

    def _execute_like(self, article: Dict) -> tuple:
        # 1. 순수 HTTP API 모드 (쿠키 제공 시)
        if self.cookies:
            return like_article_api(
                article.get("user_id", ""),
                article.get("article_no", 0),
                self.cookies,
                session=self._session
            )

        # 2. 브라우저 봇 모드 (우측 상단 하트 버튼 클릭)
        if self.bot:
            return self.bot.like_article(article.get("url", ""))

        return "ERROR", "좋아요를 수행할 인증 수단(쿠키 또는 브라우저)이 없습니다."

    def _sync_interval(self):
        """외부 콜백이 있다면 실시간 간격을 동기화합니다."""
        if self.get_interval_callback:
            try:
                cur_min, cur_max = self.get_interval_callback()
                self.interval_min = max(1, cur_min)
                self.interval_max = max(self.interval_min, cur_max)
            except Exception:
                pass

    def _run_loop(self):
        total = len(self.articles)
        mode_str = "순수 HTTP API(웹/클라우드)" if self.cookies else "셀레니움 브라우저"
        self._sync_interval()
        delay_desc = f"{self.interval_min}~{self.interval_max}초 랜덤 간격" if self.interval_min != self.interval_max else f"{self.interval_min}초 간격"
        self.log(f"[{mode_str} 모드] 총 {total}개의 글에 대해 {delay_desc} 좋아요 작업을 시작합니다.", "INFO")

        for idx, article in enumerate(self.articles):
            if self._stop_event.is_set():
                break

            # 일시 정지 대기
            while not self._pause_event.is_set():
                if self._stop_event.is_set():
                    break
                time.sleep(0.3)

            if self._stop_event.is_set():
                break

            # 이미 완료된 글은 중복 처리 방지 스킵
            if article.get("status") in ("좋아요 완료", "이미 좋아요됨"):
                self.skipped_count += 1
                self.log(f"[{idx + 1}/{total}] '{article.get('article_title')}' 이전 작업 완료 건으로 스킵합니다.", "INFO")
                continue

            self._sync_interval()
            title = article.get("article_title", "무제")
            author = article.get("user_name", "작가")

            self.log(f"[{idx + 1}/{total}] '{title}' ({author}) 우측 상단 하트 확인 중...", "INFO")
            if self.article_update_callback:
                self.article_update_callback(idx, "진행중", article)

            try:
                result_code, message = self._execute_like(article)
            except Exception as e:
                result_code, message = "ERROR", str(e)

            if result_code == "LIKED":
                self.success_count += 1
                status_str = "좋아요 완료"
                article["status"] = status_str
                self.log(f"[{idx + 1}/{total}] [성공] '{title}' 우측 상단 하트 좋아요 완료 💖", "SUCCESS")
                if self.article_completed_callback:
                    self.article_completed_callback(article, status_str)
            elif result_code == "ALREADY_LIKED":
                self.skipped_count += 1
                status_str = "이미 좋아요됨"
                article["status"] = status_str
                self.log(f"[{idx + 1}/{total}] [스킵] '{title}' 이전에 이미 좋아요를 누른 글입니다. 별도 대기 없이 다음 글로 즉시 넘어갑니다.", "INFO")
                if self.article_completed_callback:
                    self.article_completed_callback(article, status_str)
            elif result_code == "NOT_LOGGED_IN":
                self.failed_count += 1
                status_str = "로그인 필요"
                article["status"] = status_str
                self.log(f"[{idx + 1}/{total}] [실패] 로그인이 유효하지 않습니다: {message}", "ERROR")
                if self.article_update_callback:
                    self.article_update_callback(idx, status_str, article)
                break
            else:
                self.failed_count += 1
                status_str = "실패"
                article["status"] = status_str
                self.log(f"[{idx + 1}/{total}] [오류] '{title}': {message}", "ERROR")

            if self.article_update_callback:
                self.article_update_callback(idx, status_str, article)

            # 새로 좋아요를 누른 경우(LIKED)에만 1초 ~ 30초(또는 수정된 간격) 사이 무작위 지연 대기
            # 이미 좋아요를 눌렀던 글(ALREADY_LIKED)은 별도 대기 동작 없이 즉시 다음 글로 넘어감
            if result_code == "LIKED" and idx < total - 1 and not self._stop_event.is_set():
                self._sync_interval()
                wait_sec = random.randint(self.interval_min, self.interval_max)
                self.log(f"🎲 다음 글까지 {wait_sec}초 랜덤 대기 중... ({self.interval_min}~{self.interval_max}초)", "INFO")

                remaining = wait_sec
                while remaining > 0:
                    if self._stop_event.is_set():
                        break

                    # 일시 정지 중 대기
                    if not self._pause_event.is_set():
                        while not self._pause_event.is_set():
                            if self._stop_event.is_set():
                                break
                            time.sleep(0.3)
                        # 재개 후 최신 간격 동기화 및 잔여 시간 보정
                        self._sync_interval()
                        if remaining > self.interval_max:
                            remaining = self.interval_max
                            wait_sec = self.interval_max

                    if self.countdown_callback:
                        self.countdown_callback(remaining, wait_sec)
                    time.sleep(1)
                    remaining -= 1

                if self.countdown_callback:
                    self.countdown_callback(0, wait_sec)
            else:
                # 이미 좋아요되었거나 스킵된 건: 카운트다운 초기화 후 즉시 다음 루프로 진입
                if self.countdown_callback:
                    self.countdown_callback(0, 0)
                time.sleep(0.05)

        self.is_running = False
        if self._session:
            try:
                self._session.close()
            except Exception:
                pass
            self._session = None

        summary_msg = (
            f"작업 완료! [성공: {self.success_count}건, "
            f"스킵: {self.skipped_count}건, 실패: {self.failed_count}건]"
        )
        self.log(summary_msg, "SUCCESS")

        if self.on_finish_callback:
            self.on_finish_callback(self.success_count, self.skipped_count, self.failed_count)
