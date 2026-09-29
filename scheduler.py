"""
Scheduler Module
글 목록 순회 및 1분 간격 좋아요 처리 실행기
"""

import time
import threading
from typing import List, Dict, Callable, Optional
from browser_bot import BrunchBot


class LikeScheduler:
    def __init__(
        self,
        bot: BrunchBot,
        articles: List[Dict],
        interval_seconds: int = 60,
        log_callback: Optional[Callable[[str, str], None]] = None,
        article_update_callback: Optional[Callable[[int, str], None]] = None,
        countdown_callback: Optional[Callable[[int], None]] = None,
        on_finish_callback: Optional[Callable[[int, int, int], None]] = None
    ):
        """
        :param bot: BrunchBot 인스턴스
        :param articles: 처리할 글 정보 리스트
        :param interval_seconds: 좋아요 사이 간격 (기본 60초)
        :param log_callback: 로그 출력 콜백 (message, level)
        :param article_update_callback: 글 상태 업데이트 콜백 (index, status)
        :param countdown_callback: 다음 작업까지 남은 초 콜백 (remaining_seconds)
        :param on_finish_callback: 전체 완료 콜백 (success_count, skipped_count, failed_count)
        """
        self.bot = bot
        self.articles = articles
        self.interval_seconds = interval_seconds
        self.log_callback = log_callback or (lambda msg, lvl: print(f"[{lvl}] {msg}"))
        self.article_update_callback = article_update_callback
        self.countdown_callback = countdown_callback
        self.on_finish_callback = on_finish_callback

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # 시작 시 일시정지 아님

        self.success_count = 0
        self.skipped_count = 0
        self.failed_count = 0
        self.is_running = False

    def log(self, message: str, level: str = "INFO"):
        if self.log_callback:
            self.log_callback(message, level)

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
        self.log("작업이 일시 정지되었습니다.", "WARN")

    def resume(self):
        """재개"""
        self._pause_event.set()
        self.log("작업을 다시 시작합니다.", "INFO")

    def stop(self):
        """완전 중단"""
        self._stop_event.set()
        self._pause_event.set()  # 혹시 일시정지 중이면 해제하여 루프 종료 유도
        self.is_running = False
        self.log("작업 중단 요청이 접수되었습니다.", "WARN")

    def _run_loop(self):
        total = len(self.articles)
        self.log(f"총 {total}개의 글에 대해 1분({self.interval_seconds}초) 간격 좋아요 작업을 시작합니다.", "INFO")

        for idx, article in enumerate(self.articles):
            if self._stop_event.is_set():
                self.log("사용자에 의해 작업이 중단되었습니다.", "WARN")
                break

            # 일시 정지 상태 처리
            while not self._pause_event.is_set():
                if self._stop_event.is_set():
                    break
                time.sleep(0.5)

            if self._stop_event.is_set():
                break

            title = article.get("article_title", "무제")
            author = article.get("user_name", "작가")
            url = article.get("url", "")

            self.log(f"[{idx + 1}/{total}] '{title}' ({author}) 페이지 접속 중...", "INFO")
            if self.article_update_callback:
                self.article_update_callback(idx, "진행중")

            # 좋아요 수행
            result_code, message = self.bot.like_article(url)

            if result_code == "LIKED":
                self.success_count += 1
                status_str = "좋아요 완료"
                self.log(f"[{idx + 1}/{total}] [성공] '{title}' 좋아요를 눌렀습니다.", "SUCCESS")
            elif result_code == "ALREADY_LIKED":
                self.skipped_count += 1
                status_str = "이미 좋아요됨"
                self.log(f"[{idx + 1}/{total}] [스킵] '{title}' 이미 좋아요가 되어 있습니다.", "INFO")
            elif result_code == "NOT_LOGGED_IN":
                self.failed_count += 1
                status_str = "로그인 필요"
                self.log(f"[{idx + 1}/{total}] [실패] 로그인이 되어있지 않습니다. 작업을 중단합니다.", "ERROR")
                if self.article_update_callback:
                    self.article_update_callback(idx, status_str)
                break
            else:
                self.failed_count += 1
                status_str = "실패"
                self.log(f"[{idx + 1}/{total}] [오류] '{title}': {message}", "ERROR")

            if self.article_update_callback:
                self.article_update_callback(idx, status_str)

            # 마지막 글이 아니라면 1분(interval_seconds) 카운트다운 대기
            if idx < total - 1 and not self._stop_event.is_set():
                self.log(f"다음 글 좋아요까지 {self.interval_seconds}초 대기합니다...", "INFO")
                for remaining in range(self.interval_seconds, 0, -1):
                    if self._stop_event.is_set():
                        break
                    while not self._pause_event.is_set():
                        if self._stop_event.is_set():
                            break
                        time.sleep(0.5)

                    if self.countdown_callback:
                        self.countdown_callback(remaining)
                    time.sleep(1)

                if self.countdown_callback:
                    self.countdown_callback(0)

        self.is_running = False
        summary_msg = (
            f"작업 완료! [성공: {self.success_count}건, "
            f"스킵(기존좋아요): {self.skipped_count}건, 실패: {self.failed_count}건]"
        )
        self.log(summary_msg, "SUCCESS")

        if self.on_finish_callback:
            self.on_finish_callback(self.success_count, self.skipped_count, self.failed_count)
