"""
Brunch Like Tool - Desktop GUI
브런치 특정 요일 연재글 1분 간격 자동 좋아요 데스크톱 애플리케이션
- 브라우저 자동 로그인(Selenium) 및 쿠키 직접 입력(순수 API) 모드 완벽 지원
"""

import os
import sys
import time
import webbrowser
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
from datetime import datetime

# 로컬 모듈 로드
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from brunch_api import fetch_serial_articles, check_user_session, parse_cookie_string, DAY_MAP, ORDER_MAP
from browser_bot import BrunchBot
from scheduler import LikeScheduler


class BrunchLikeApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("브런치 연재글 자동 좋아요 도구 (Brunch Like Tool)")
        self.root.geometry("1040x780")
        self.root.minsize(920, 700)

        # 상태 변수
        self.articles = []
        self.bot = None
        self.scheduler = None
        self.cookie_str = ""
        self.is_paused = False

        self._init_styles()
        self._build_ui()

    def _init_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(".", font=("Malgun Gothic", 9))
        style.configure("Header.TLabel", font=("Malgun Gothic", 15, "bold"), foreground="#1e293b")
        style.configure("SubHeader.TLabel", font=("Malgun Gothic", 9), foreground="#64748b")
        style.configure("Card.TLabelframe", background="#ffffff")
        style.configure("Card.TLabelframe.Label", font=("Malgun Gothic", 10, "bold"), foreground="#0f172a")

        style.configure("Primary.TButton", font=("Malgun Gothic", 9, "bold"), foreground="#ffffff", background="#00c6be")
        style.map("Primary.TButton", background=[("active", "#00a39d")])

        style.configure("Action.TButton", font=("Malgun Gothic", 10, "bold"), foreground="#ffffff", background="#2563eb")
        style.map("Action.TButton", background=[("active", "#1d4ed8")])

        style.configure("Stop.TButton", font=("Malgun Gothic", 9, "bold"), foreground="#ffffff", background="#ef4444")
        style.map("Stop.TButton", background=[("active", "#dc2626")])

    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding=12)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. 상단 타이틀 영역
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        title_lbl = ttk.Label(header_frame, text="✨ 브런치 연재글 1분 간격 자동 좋아요", style="Header.TLabel")
        title_lbl.pack(anchor="w")

        desc_lbl = ttk.Label(
            header_frame,
            text="목표 URL: https://brunch.co.kr/serial/list#tue#PUBLISH_TIME (설정한 요일의 최신 연재 글을 순차적으로 1분 간격 좋아요)",
            style="SubHeader.TLabel"
        )
        desc_lbl.pack(anchor="w", pady=(2, 0))

        # 2. 설정 및 컨트롤 카드 영역
        control_frame = ttk.LabelFrame(main_frame, text=" ⚙️ 실행 설정 및 로그인 ", padding=10, style="Card.TLabelframe")
        control_frame.pack(fill=tk.X, pady=(0, 10))

        # 1행: 요일, 정렬, 간격, 브라우저/모드
        row1 = ttk.Frame(control_frame)
        row1.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(row1, text="요일 선택:").pack(side=tk.LEFT, padx=(0, 4))
        self.day_var = tk.StringVar(value="화요일 (tue)")
        day_combo = ttk.Combobox(
            row1,
            textvariable=self.day_var,
            values=[
                "월요일 (mon)", "화요일 (tue)", "수요일 (wed)", "목요일 (thu)",
                "금요일 (fri)", "토요일 (sat)", "일요일 (sun)", "완결작 (com)"
            ],
            width=14,
            state="readonly"
        )
        day_combo.pack(side=tk.LEFT, padx=(0, 15))
        day_combo.bind("<<ComboboxSelected>>", self._on_setting_changed)

        ttk.Label(row1, text="정렬 기준:").pack(side=tk.LEFT, padx=(0, 4))
        self.order_var = tk.StringVar(value="최신순 (PUBLISH_TIME)")
        order_combo = ttk.Combobox(
            row1,
            textvariable=self.order_var,
            values=["최신순 (PUBLISH_TIME)", "인기순 (POPULARITY)"],
            width=20,
            state="readonly"
        )
        order_combo.pack(side=tk.LEFT, padx=(0, 15))
        order_combo.bind("<<ComboboxSelected>>", self._on_setting_changed)

        ttk.Label(row1, text="좋아요 간격 (랜덤):").pack(side=tk.LEFT, padx=(0, 4))
        self.interval_min_var = tk.IntVar(value=1)
        spin_min = ttk.Spinbox(row1, from_=1, to=120, textvariable=self.interval_min_var, width=4)
        spin_min.pack(side=tk.LEFT, padx=(0, 2))
        ttk.Label(row1, text="초 ~").pack(side=tk.LEFT, padx=(0, 2))
        self.interval_max_var = tk.IntVar(value=30)
        spin_max = ttk.Spinbox(row1, from_=1, to=120, textvariable=self.interval_max_var, width=4)
        spin_max.pack(side=tk.LEFT, padx=(0, 2))
        ttk.Label(row1, text="초 사이").pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(row1, text="브라우저:").pack(side=tk.LEFT, padx=(0, 4))
        self.browser_var = tk.StringVar(value="chrome")
        browser_combo = ttk.Combobox(
            row1,
            textvariable=self.browser_var,
            values=["chrome", "edge"],
            width=8,
            state="readonly"
        )
        browser_combo.pack(side=tk.LEFT, padx=(0, 10))

        # 2행: 주요 버튼 그룹 (로그인, 쿠키입력, 목록조회, 시작, 일시정지, 중단)
        row2 = ttk.Frame(control_frame)
        row2.pack(fill=tk.X)

        self.btn_login = ttk.Button(row2, text="🔑 1. 카카오 로그인 브라우저 열기", command=self._open_login_window)
        self.btn_login.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_cookie = ttk.Button(row2, text="🍪 쿠키 직접 입력", command=self._open_cookie_dialog)
        self.btn_cookie.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_fetch = ttk.Button(row2, text="📋 2. 연재 글 목록 불러오기", command=self._fetch_articles)
        self.btn_fetch.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_start = ttk.Button(row2, text="🚀 3. 자동 좋아요 시작", command=self._start_like, style="Action.TButton")
        self.btn_start.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_pause = ttk.Button(row2, text="⏸️ 일시정지", command=self._toggle_pause, state="disabled")
        self.btn_pause.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_stop = ttk.Button(row2, text="⏹️ 중단", command=self._stop_like, style="Stop.TButton", state="disabled")
        self.btn_stop.pack(side=tk.LEFT)

        # 3. 진행 상태 바 & 안내 레이블
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(0, 8))

        self.status_lbl = ttk.Label(status_frame, text="대기 중 - 목록을 불러온 후 좋아요를 시작하세요.", font=("Malgun Gothic", 9, "bold"))
        self.status_lbl.pack(side=tk.LEFT)

        self.countdown_lbl = ttk.Label(status_frame, text="", foreground="#dc2626", font=("Malgun Gothic", 9, "bold"))
        self.countdown_lbl.pack(side=tk.RIGHT)

        self.progress_bar = ttk.Progressbar(main_frame, mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))

        # 4. 중앙 분할 (글 목록 테이블 + 실시간 로그)
        paned = ttk.PanedWindow(main_frame, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True)

        table_card = ttk.LabelFrame(paned, text=" 📑 연재 글 목록 (더블클릭 시 브라우저로 글 열기) ", padding=5)
        paned.add(table_card, weight=3)

        cols = ("idx", "title", "author", "magazine", "date", "likes", "status")
        self.tree = ttk.Treeview(table_card, columns=cols, show="headings", selectmode="browse")

        self.tree.heading("idx", text="#")
        self.tree.heading("title", text="글 제목")
        self.tree.heading("author", text="작가")
        self.tree.heading("magazine", text="매거진/브런치북")
        self.tree.heading("date", text="발행일시")
        self.tree.heading("likes", text="좋아요")
        self.tree.heading("status", text="처리 상태")

        self.tree.column("idx", width=40, anchor="center")
        self.tree.column("title", width=280)
        self.tree.column("author", width=100)
        self.tree.column("magazine", width=180)
        self.tree.column("date", width=120, anchor="center")
        self.tree.column("likes", width=60, anchor="center")
        self.tree.column("status", width=110, anchor="center")

        tree_scroll = ttk.Scrollbar(table_card, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<Double-1>", self._on_row_double_click)

        log_card = ttk.LabelFrame(paned, text=" 📝 실시간 실행 로그 ", padding=5)
        paned.add(log_card, weight=2)

        self.log_text = scrolledtext.ScrolledText(log_card, height=8, font=("Consolas", 9), wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self.log_text.tag_config("INFO", foreground="#1e293b")
        self.log_text.tag_config("SUCCESS", foreground="#16a34a", font=("Consolas", 9, "bold"))
        self.log_text.tag_config("WARN", foreground="#d97706", font=("Consolas", 9, "bold"))
        self.log_text.tag_config("ERROR", foreground="#dc2626", font=("Consolas", 9, "bold"))

        self._log("브런치 연재글 자동 좋아요 프로그램이 준비되었습니다.", "INFO")
        self._log("💡 브라우저 자동 로그인 또는 [쿠키 직접 입력] 둘 중 편한 방식을 선택하세요.", "INFO")

    def _log(self, msg: str, level: str = "INFO"):
        now = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{now}] [{level}] {msg}\n"

        def append():
            self.log_text.insert(tk.END, formatted, level)
            self.log_text.see(tk.END)

        self.root.after(0, append)

    def _get_selected_day_code(self) -> str:
        text = self.day_var.get()
        if "(" in text and ")" in text:
            return text.split("(")[1].split(")")[0].strip()
        return "tue"

    def _get_selected_order_code(self) -> str:
        text = self.order_var.get()
        if "POPULARITY" in text:
            return "POPULARITY"
        return "PUBLISH_TIME"

    def _on_setting_changed(self, event=None):
        day_code = self._get_selected_day_code()
        order_code = self._get_selected_order_code()
        self._log(f"설정 변경: 요일={day_code}, 정렬={order_code}", "INFO")

    def _open_login_window(self):
        browser = self.browser_var.get()
        self._log(f"[{browser.upper()}] 카카오 로그인 창을 엽니다...", "INFO")

        def task():
            try:
                if not self.bot:
                    self.bot = BrunchBot(browser_type=browser)
                self.bot.open_login_window(on_login_success=lambda: self._log("카카오 로그인 성공이 감지되었습니다!", "SUCCESS"))
            except Exception as e:
                self._log(f"브라우저 실행 오류: {e}", "ERROR")

        threading.Thread(target=task, daemon=True).start()

    def _open_cookie_dialog(self):
        cookie = simpledialog.askstring(
            "브런치 쿠키 직접 입력",
            "브런치 로그인 쿠키 문자열을 붙여넣으세요:\n(예: b_uid=...; brunch_session=...)",
            parent=self.root
        )
        if cookie:
            self.cookie_str = cookie.strip()
            is_ok, user = check_user_session(self.cookie_str)
            if is_ok:
                self._log(f"[쿠키 인증 성공] '{user}' 작가님 계정으로 확인되었습니다.", "SUCCESS")
                messagebox.showinfo("인증 성공", f"쿠키 세션 검증 성공!\n인증 계정: {user}")
            else:
                self._log(f"[쿠키 인증 경고] 세션 확인 실패: {user}", "WARN")
                messagebox.showwarning("인증 경고", f"세션 검증 실패: {user}\n쿠키를 다시 확인해주세요.")

    def _fetch_articles(self):
        day_code = self._get_selected_day_code()
        order_code = self._get_selected_order_code()
        self._log(f"'{day_code}' 요일 ({order_code}) 연재 글 목록을 불러오는 중...", "INFO")
        self.status_lbl.config(text="글 목록 불러오는 중...")

        def task():
            try:
                items = fetch_serial_articles(
                    day=day_code,
                    order=order_code,
                    progress_callback=lambda count: self.root.after(
                        0, lambda: self.status_lbl.config(text=f"글 목록 수집 중... ({count}개)")
                    )
                )
                self.articles = items

                def update_tree():
                    for row in self.tree.get_children():
                        self.tree.delete(row)

                    for idx, art in enumerate(self.articles):
                        self.tree.insert(
                            "",
                            tk.END,
                            iid=str(idx),
                            values=(
                                idx + 1,
                                art["article_title"],
                                art["user_name"],
                                art["magazine_title"],
                                art["publish_date_str"],
                                art["like_count"],
                                art["status"]
                            )
                        )

                    self.status_lbl.config(text=f"글 목록 불러오기 완료: 총 {len(self.articles)}건")
                    self.progress_bar.config(maximum=max(1, len(self.articles)), value=0)
                    self._log(f"총 {len(self.articles)}개의 글 목록을 성공적으로 불러왔습니다.", "SUCCESS")

                self.root.after(0, update_tree)
            except Exception as e:
                self._log(f"목록 수집 실패: {e}", "ERROR")

        threading.Thread(target=task, daemon=True).start()

    def _start_like(self):
        if not self.articles:
            messagebox.showwarning("안내", "먼저 [2. 연재 글 목록 불러오기]를 눌러 글 목록을 조회해주세요.")
            return

        min_sec = max(1, self.interval_min_var.get())
        max_sec = max(min_sec, self.interval_max_var.get())

        browser = self.browser_var.get()
        bot_instance = None
        if not self.cookie_str:
            if not self.bot:
                self.bot = BrunchBot(browser_type=browser)
            bot_instance = self.bot

        self.btn_start.config(state="disabled")
        self.btn_pause.config(state="normal", text="⏸️ 일시정지")
        self.btn_stop.config(state="normal")
        self.btn_fetch.config(state="disabled")

        self.scheduler = LikeScheduler(
            articles=self.articles,
            interval_min=min_sec,
            interval_max=max_sec,
            bot=bot_instance,
            cookies=self.cookie_str if self.cookie_str else None,
            log_callback=self._log,
            article_update_callback=self._update_article_status,
            countdown_callback=self._update_countdown,
            on_finish_callback=self._on_schedule_finish
        )
        self.scheduler.start()

    def _update_article_status(self, idx: int, status: str):
        def cb():
            try:
                self.articles[idx]["status"] = status
                self.tree.set(str(idx), "status", status)
                self.progress_bar.config(value=idx + 1)
                self.status_lbl.config(text=f"진행 중: [{idx + 1}/{len(self.articles)}] '{self.articles[idx]['article_title']}'")
            except Exception:
                pass
        self.root.after(0, cb)

    def _update_countdown(self, remaining: int, total_wait: int = 0):
        def cb():
            if remaining > 0:
                self.countdown_lbl.config(text=f"⏳ 다음 글까지 랜덤 대기: {remaining}초 / {total_wait}초")
            else:
                self.countdown_lbl.config(text="")
        self.root.after(0, cb)

    def _on_schedule_finish(self, success: int, skipped: int, failed: int):
        def cb():
            self.btn_start.config(state="normal")
            self.btn_pause.config(state="disabled", text="⏸️ 일시정지")
            self.btn_stop.config(state="disabled")
            self.btn_fetch.config(state="normal")
            self.countdown_lbl.config(text="")
            self.status_lbl.config(text=f"작업 완료 - 성공: {success}건, 스킵: {skipped}건, 실패: {failed}건")
            messagebox.showinfo("완료", f"좋아요 작업이 완료되었습니다!\n- 성공: {success}건\n- 스킵(이미좋아요): {skipped}건\n- 실패: {failed}건")
        self.root.after(0, cb)

    def _toggle_pause(self):
        if not self.scheduler:
            return

        if self.is_paused:
            self.scheduler.resume()
            self.btn_pause.config(text="⏸️ 일시정지")
            self.is_paused = False
        else:
            self.scheduler.pause()
            self.btn_pause.config(text="▶️ 재개")
            self.is_paused = True

    def _stop_like(self):
        if self.scheduler:
            self.scheduler.stop()
        self.btn_start.config(state="normal")
        self.btn_pause.config(state="disabled")
        self.btn_stop.config(state="disabled")
        self.btn_fetch.config(state="normal")
        self.countdown_lbl.config(text="")

    def _on_row_double_click(self, event):
        item_id = self.tree.focus()
        if not item_id:
            return
        idx = int(item_id)
        if 0 <= idx < len(self.articles):
            url = self.articles[idx]["url"]
            webbrowser.open(url)


def main():
    root = tk.Tk()
    app = BrunchLikeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
