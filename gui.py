"""
Brunch Like Tool - Desktop GUI
브런치 특정 요일 연재글 자동 좋아요 데스크톱 애플리케이션
- 실행 중/일시정지 중 좋아요 간격 실시간 수정 및 즉시 반영
- '대기 중인 글 목록'과 '좋아요 완료 목록' 탭 분리 관리
- 중단 후 재시작 시 이미 완료된 글 중복 좋아요 원천 방지 (세션/로컬 영구 캐시)
- 브라우저 자동 로그인(Selenium) 및 쿠키 직접 입력(순수 API) 모드 지원
"""

import os
import sys
import json
import time
import webbrowser
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
from datetime import datetime
from typing import Tuple, Dict, Optional

# 로컬 모듈 로드
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from brunch_api import fetch_serial_articles, check_user_session, normalize_day, normalize_order
from browser_bot import BrunchBot
from scheduler import LikeScheduler


class BrunchLikeApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("브런치 연재글 자동 좋아요 도구 (Brunch Like Tool)")
        self.root.geometry("1060x800")
        self.root.minsize(940, 720)

        # 상태 변수
        self.articles = []            # 전체 수집된 원본 목록
        self.pending_articles = []    # 대기 중인 글 목록
        self.completed_articles = []  # 좋아요 완료/스킵된 글 목록
        self.completed_keys = set()   # 완료된 글 고유 키 세트 (중복 방지)

        self.bot = None
        self.scheduler = None
        self.cookie_str = ""
        self.is_paused = False

        self.cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brunch_profile")
        os.makedirs(self.cache_dir, exist_ok=True)
        self.cache_file = os.path.join(self.cache_dir, "completed_articles.json")
        self._load_completed_cache()

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

    def _load_completed_cache(self):
        """이전에 좋아요 완료한 글 목록을 캐시 파일에서 로드합니다."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.completed_keys = set(data.get("keys", []))
                    self.completed_articles = data.get("articles", [])
            except Exception:
                self.completed_keys = set()
                self.completed_articles = []

    def _save_completed_cache(self):
        """완료된 글 목록을 로컬 캐시 파일에 저장합니다."""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump({
                    "keys": list(self.completed_keys),
                    "articles": self.completed_articles
                }, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding=12)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. 상단 타이틀 영역
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        title_lbl = ttk.Label(header_frame, text="✨ 브런치 연재글 자동 좋아요 도구", style="Header.TLabel")
        title_lbl.pack(anchor="w")

        desc_lbl = ttk.Label(
            header_frame,
            text="목표 URL: https://brunch.co.kr/serial/list#tue#PUBLISH_TIME (우측 상단 하트 기준, 실시간 간격 수정 및 중복 방지)",
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

        ttk.Label(row1, text="좋아요 간격 (실시간 수정 가능):", font=("Malgun Gothic", 9, "bold"), foreground="#0284c7").pack(side=tk.LEFT, padx=(0, 4))
        self.interval_min_var = tk.IntVar(value=1)
        spin_min = ttk.Spinbox(row1, from_=1, to=120, textvariable=self.interval_min_var, width=4)
        spin_min.pack(side=tk.LEFT, padx=(0, 2))
        ttk.Label(row1, text="초 ~").pack(side=tk.LEFT, padx=(0, 2))
        self.interval_max_var = tk.IntVar(value=30)
        spin_max = ttk.Spinbox(row1, from_=1, to=120, textvariable=self.interval_max_var, width=4)
        spin_max.pack(side=tk.LEFT, padx=(0, 2))
        ttk.Label(row1, text="초 사이").pack(side=tk.LEFT, padx=(0, 15))

        # 간격 실시간 수정 감지 바인딩
        self.interval_min_var.trace_add("write", lambda *args: self._on_interval_modified())
        self.interval_max_var.trace_add("write", lambda *args: self._on_interval_modified())

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

        # 2행: 주요 버튼 그룹
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
        self.btn_stop.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_clear_done = ttk.Button(row2, text="🗑️ 완료 이력 초기화", command=self._clear_completed_cache)
        self.btn_clear_done.pack(side=tk.RIGHT)

        # 3. 진행 상태 바 & 안내 레이블
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(0, 8))

        self.status_lbl = ttk.Label(status_frame, text="대기 중 - 목록을 불러온 후 좋아요를 시작하세요.", font=("Malgun Gothic", 9, "bold"))
        self.status_lbl.pack(side=tk.LEFT)

        self.countdown_lbl = ttk.Label(status_frame, text="", foreground="#dc2626", font=("Malgun Gothic", 9, "bold"))
        self.countdown_lbl.pack(side=tk.RIGHT)

        self.progress_bar = ttk.Progressbar(main_frame, mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))

        # 4. 중앙 분할 (글 목록 탭 + 실시간 로그)
        paned = ttk.PanedWindow(main_frame, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True)

        table_card = ttk.LabelFrame(paned, text=" 📑 연재 글 목록 (더블클릭 시 브라우저로 글 열기) ", padding=5)
        paned.add(table_card, weight=3)

        # 탭 노트북 생성 (대기 목록 / 완료 목록)
        self.notebook = ttk.Notebook(table_card)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # [탭 1] 대기 중인 글 목록
        self.tab_pending = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_pending, text="📑 대기 중인 글 목록 (0건)")

        cols_pending = ("idx", "title", "author", "magazine", "date", "likes", "status")
        self.tree_pending = ttk.Treeview(self.tab_pending, columns=cols_pending, show="headings", selectmode="browse")
        self.tree_pending.heading("idx", text="#")
        self.tree_pending.heading("title", text="글 제목")
        self.tree_pending.heading("author", text="작가")
        self.tree_pending.heading("magazine", text="매거진/브런치북")
        self.tree_pending.heading("date", text="발행일시")
        self.tree_pending.heading("likes", text="좋아요")
        self.tree_pending.heading("status", text="처리 상태")

        self.tree_pending.column("idx", width=40, anchor="center")
        self.tree_pending.column("title", width=280)
        self.tree_pending.column("author", width=100)
        self.tree_pending.column("magazine", width=170)
        self.tree_pending.column("date", width=120, anchor="center")
        self.tree_pending.column("likes", width=60, anchor="center")
        self.tree_pending.column("status", width=110, anchor="center")

        scroll_p = ttk.Scrollbar(self.tab_pending, orient=tk.VERTICAL, command=self.tree_pending.yview)
        self.tree_pending.configure(yscrollcommand=scroll_p.set)
        self.tree_pending.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_p.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_pending.bind("<Double-1>", self._on_pending_double_click)

        # [탭 2] 좋아요 완료 목록
        self.tab_done = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_done, text=f"💖 좋아요 완료 목록 ({len(self.completed_articles)}건)")

        cols_done = ("idx", "title", "author", "magazine", "date", "status", "time")
        self.tree_done = ttk.Treeview(self.tab_done, columns=cols_done, show="headings", selectmode="browse")
        self.tree_done.heading("idx", text="#")
        self.tree_done.heading("title", text="글 제목")
        self.tree_done.heading("author", text="작가")
        self.tree_done.heading("magazine", text="매거진/브런치북")
        self.tree_done.heading("date", text="발행일시")
        self.tree_done.heading("status", text="처리 결과")
        self.tree_done.heading("time", text="완료 시각")

        self.tree_done.column("idx", width=40, anchor="center")
        self.tree_done.column("title", width=280)
        self.tree_done.column("author", width=100)
        self.tree_done.column("magazine", width=170)
        self.tree_done.column("date", width=120, anchor="center")
        self.tree_done.column("status", width=110, anchor="center")
        self.tree_done.column("time", width=100, anchor="center")

        scroll_d = ttk.Scrollbar(self.tab_done, orient=tk.VERTICAL, command=self.tree_done.yview)
        self.tree_done.configure(yscrollcommand=scroll_d.set)
        self.tree_done.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_d.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_done.bind("<Double-1>", self._on_done_double_click)

        # 기존 캐시된 완료 목록 표시
        self._refresh_done_tree()

        # 하단 로그 카드
        log_card = ttk.LabelFrame(paned, text=" 📝 실시간 실행 로그 ", padding=5)
        paned.add(log_card, weight=2)

        self.log_text = scrolledtext.ScrolledText(log_card, height=8, font=("Consolas", 9), wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self.log_text.tag_config("INFO", foreground="#1e293b")
        self.log_text.tag_config("SUCCESS", foreground="#16a34a", font=("Consolas", 9, "bold"))
        self.log_text.tag_config("WARN", foreground="#d97706", font=("Consolas", 9, "bold"))
        self.log_text.tag_config("ERROR", foreground="#dc2626", font=("Consolas", 9, "bold"))

        self._log("브런치 연재글 자동 좋아요 프로그램이 준비되었습니다.", "INFO")
        self._log("💡 대기 목록과 완료 목록이 탭으로 분리되어, 중단 후 시작 시 중복 좋아요가 방지됩니다.", "INFO")
        self._log("⚡ 실행 중 또는 일시정지 중 간격 숫자를 수정하면 새 간격이 즉시 반영됩니다.", "INFO")

    def _log(self, msg: str, level: str = "INFO"):
        now = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{now}] [{level}] {msg}\n"

        def append():
            self.log_text.insert(tk.END, formatted, level)
            self.log_text.see(tk.END)

        self.root.after(0, append)

    def _get_current_interval(self) -> Tuple[int, int]:
        """현재 UI 스핀박스에 입력된 최소/최대 초를 가져옵니다."""
        try:
            min_sec = max(1, self.interval_min_var.get())
            max_sec = max(min_sec, self.interval_max_var.get())
            return min_sec, max_sec
        except Exception:
            return 1, 30

    def _on_interval_modified(self):
        """사용자가 간격 숫자를 수정한 즉시 스케줄러에 동기화합니다."""
        if self.scheduler and self.scheduler.is_running:
            min_sec, max_sec = self._get_current_interval()
            self.scheduler.update_interval(min_sec, max_sec)

    def _get_selected_day_code(self) -> str:
        text = self.day_var.get()
        if "(" in text and ")" in text:
            raw = text.split("(")[1].split(")")[0].strip()
            return normalize_day(raw)
        return normalize_day(text)

    def _get_selected_order_code(self) -> str:
        return normalize_order(self.order_var.get())

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

    def _get_article_key(self, art: Dict) -> str:
        return f"{art.get('user_id', '')}_{art.get('article_no', 0)}"

    def _refresh_done_tree(self):
        """완료 탭 트리를 갱신합니다."""
        for row in self.tree_done.get_children():
            self.tree_done.delete(row)

        for idx, art in enumerate(self.completed_articles):
            self.tree_done.insert(
                "",
                tk.END,
                iid=f"done_{idx}",
                values=(
                    idx + 1,
                    art.get("article_title", "무제"),
                    art.get("user_name", "작가"),
                    art.get("magazine_title", "-"),
                    art.get("publish_date_str", "-"),
                    art.get("status", "완료"),
                    art.get("done_time", "-")
                )
            )
        self.notebook.tab(1, text=f"💖 좋아요 완료 목록 ({len(self.completed_articles)}건)")

    def _refresh_pending_tree(self):
        """대기 탭 트리를 갱신합니다."""
        for row in self.tree_pending.get_children():
            self.tree_pending.delete(row)

        for idx, art in enumerate(self.pending_articles):
            self.tree_pending.insert(
                "",
                tk.END,
                iid=f"pending_{idx}",
                values=(
                    idx + 1,
                    art.get("article_title", "무제"),
                    art.get("user_name", "작가"),
                    art.get("magazine_title", "-"),
                    art.get("publish_date_str", "-"),
                    art.get("like_count", 0),
                    art.get("status", "대기중")
                )
            )
        self.notebook.tab(0, text=f"📑 대기 중인 글 목록 ({len(self.pending_articles)}건)")

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

                # 완료된 글과 대기 중인 글 자동 분리
                new_pending = []
                for art in items:
                    key = self._get_article_key(art)
                    if key in self.completed_keys:
                        # 이미 완료 목록에 있는 글
                        continue
                    new_pending.append(art)

                self.pending_articles = new_pending

                def update_ui():
                    self._refresh_pending_tree()
                    self._refresh_done_tree()
                    self.status_lbl.config(
                        text=f"글 목록 불러오기 완료: 대기 {len(self.pending_articles)}건 / 완료 {len(self.completed_articles)}건"
                    )
                    self.progress_bar.config(maximum=max(1, len(self.pending_articles)), value=0)
                    self._log(
                        f"총 {len(items)}건 중 [대기: {len(self.pending_articles)}건 / 기완료: {len(self.completed_articles)}건] 정리 완료.",
                        "SUCCESS"
                    )

                self.root.after(0, update_ui)
            except Exception as e:
                self._log(f"목록 수집 실패: {e}", "ERROR")

        threading.Thread(target=task, daemon=True).start()

    def _on_article_completed(self, article: Dict, status_str: str):
        """좋아요 완료 또는 스킵된 글을 대기 탭에서 완료 탭으로 실시간 이동합니다."""
        def cb():
            key = self._get_article_key(article)
            if key not in self.completed_keys:
                self.completed_keys.add(key)
                article["status"] = status_str
                article["done_time"] = datetime.now().strftime("%H:%M:%S")
                self.completed_articles.insert(0, article)
                self._save_completed_cache()

            # pending_articles에서 제거
            self.pending_articles = [a for a in self.pending_articles if self._get_article_key(a) != key]
            self._refresh_pending_tree()
            self._refresh_done_tree()

        self.root.after(0, cb)

    def _start_like(self):
        # 대기 중인 글 중 아직 완료되지 않은 글만 추출
        targets = [
            a for a in self.pending_articles
            if self._get_article_key(a) not in self.completed_keys and a.get("status") not in ("좋아요 완료", "이미 좋아요됨")
        ]

        if not targets:
            messagebox.showinfo("안내", "대기 중인 글이 없거나 모든 글의 좋아요가 이미 완료되었습니다!")
            return

        min_sec, max_sec = self._get_current_interval()
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
        self.progress_bar.config(maximum=len(targets), value=0)

        # 탭을 자동으로 대기 목록으로 전환
        self.notebook.select(0)

        self.scheduler = LikeScheduler(
            articles=targets,
            interval_min=min_sec,
            interval_max=max_sec,
            bot=bot_instance,
            cookies=self.cookie_str if self.cookie_str else None,
            log_callback=self._log,
            article_update_callback=self._update_article_progress,
            article_completed_callback=self._on_article_completed,
            countdown_callback=self._update_countdown,
            on_finish_callback=self._on_schedule_finish,
            get_interval_callback=self._get_current_interval
        )
        self.scheduler.start()

    def _update_article_progress(self, idx: int, status: str, article: Optional[Dict] = None):
        def cb():
            try:
                self.progress_bar.config(value=idx + 1)
                title = ""
                if article:
                    title = article.get("article_title", "")
                elif idx < len(self.pending_articles):
                    title = self.pending_articles[idx].get("article_title", "")

                max_val = int(self.progress_bar.cget("maximum") or len(self.pending_articles) or 1)
                if status == "진행중":
                    self.status_lbl.config(
                        text=f"진행 중: [{idx + 1}/{max_val}] '{title}'"
                    )
                elif status == "이미 좋아요됨":
                    self.status_lbl.config(
                        text=f"스킵: [{idx + 1}/{max_val}] '{title}' (이전 좋아요 완료 건 ⏩)"
                    )
            except Exception:
                pass
        self.root.after(0, cb)

    def _update_countdown(self, remaining: int, total_wait: int = 0):
        def cb():
            if remaining > 0:
                self.countdown_lbl.config(text=f"⏳ 다음 글까지 랜덤 대기: {remaining}초 / {total_wait}초 (실시간 간격 수정 가능)")
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
            self.notebook.select(1)  # 완료 후 완료 탭으로 이동
            messagebox.showinfo("완료", f"좋아요 작업이 완료되었습니다!\n- 성공: {success}건\n- 스킵(기완료): {skipped}건\n- 실패: {failed}건\n\n완료된 글은 [좋아요 완료 목록] 탭으로 이동되었습니다.")
        self.root.after(0, cb)

    def _toggle_pause(self):
        if not self.scheduler:
            return

        if self.is_paused:
            new_min, new_max = self._get_current_interval()
            self.scheduler.update_interval(new_min, new_max)
            self._log(f"수정된 대기 간격({new_min}~{new_max}초)을 즉시 적용하여 작업을 재개합니다.", "INFO")
            self.scheduler.resume()
            self.btn_pause.config(text="⏸️ 일시정지")
            self.is_paused = False
        else:
            self.scheduler.pause()
            self.btn_pause.config(text="▶️ 재개 (간격 수정 후 클릭)")
            self.is_paused = True

    def _stop_like(self):
        if self.scheduler:
            self.scheduler.stop()
        self.btn_start.config(state="normal")
        self.btn_pause.config(state="disabled", text="⏸️ 일시정지")
        self.btn_stop.config(state="disabled")
        self.btn_fetch.config(state="normal")
        self.countdown_lbl.config(text="")
        self.is_paused = False
        self._log("작업이 중단되었습니다. 완료된 글은 완료 탭에 보존되어 재시작 시 중복 좋아요가 방지됩니다.", "WARN")

    def _clear_completed_cache(self):
        """완료 이력을 초기화합니다."""
        if not self.completed_articles:
            messagebox.showinfo("안내", "초기화할 완료 이력이 없습니다.")
            return

        if messagebox.askyesno("확인", "좋아요 완료 목록과 중복 방지 이력을 모두 초기화하시겠습니까?"):
            self.completed_keys.clear()
            self.completed_articles.clear()
            self._save_completed_cache()
            self._refresh_done_tree()
            self._log("좋아요 완료 이력이 초기화되었습니다.", "INFO")

    def _on_pending_double_click(self, event):
        item_id = self.tree_pending.focus()
        if not item_id:
            return
        try:
            idx = int(item_id.replace("pending_", ""))
            if 0 <= idx < len(self.pending_articles):
                webbrowser.open(self.pending_articles[idx]["url"])
        except Exception:
            pass

    def _on_done_double_click(self, event):
        item_id = self.tree_done.focus()
        if not item_id:
            return
        try:
            idx = int(item_id.replace("done_", ""))
            if 0 <= idx < len(self.completed_articles):
                webbrowser.open(self.completed_articles[idx]["url"])
        except Exception:
            pass


def main():
    root = tk.Tk()
    app = BrunchLikeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
