#!/usr/bin/env python3
"""Plain Tk manager for AdsPower ChatGPT browser profiles."""

from __future__ import annotations

import csv
import os
import queue
import random
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any, Dict, List, Optional

from adspower_open_chatgpt import (
    DEFAULT_BASE_URL,
    DEFAULT_PROXY_FILE,
    DEFAULT_TARGET_URL,
    AdsPowerError,
    check_connection,
    create_profile,
    load_proxies,
    open_profile,
    open_url_by_debug_port,
    request_json,
)


BG = "#f5f7fb"
PANEL = "#ffffff"
TEXT = "#111827"
MUTED = "#4b5563"
LINE = "#d1d5db"
BLUE = "#2563eb"
RED = "#dc2626"


class AdsPowerGui(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("AdsPower 环境管理")
        self.geometry("1120x760")
        self.minsize(980, 640)
        self.configure(bg=BG)

        self.events: "queue.Queue[tuple[str, Any]]" = queue.Queue()
        self.emails: List[str] = []
        self.profiles: List[Dict[str, Any]] = []

        self.base_url_var = tk.StringVar(value=os.getenv("ADSPOWER_BASE_URL", DEFAULT_BASE_URL))
        self.api_key_var = tk.StringVar(value=os.getenv("ADSPOWER_API_KEY", ""))
        self.group_id_var = tk.StringVar(value=os.getenv("ADSPOWER_GROUP_ID", "0"))
        self.url_var = tk.StringVar(value=os.getenv("ADSPOWER_TARGET_URL", DEFAULT_TARGET_URL))
        self.proxy_file_var = tk.StringVar(value=os.getenv("ADSPOWER_PROXY_FILE", DEFAULT_PROXY_FILE))
        self.count_var = tk.StringVar(value="1")
        self.profile_ids_var = tk.StringVar(value="")
        self.open_after_var = tk.IntVar(value=1)
        self.status_var = tk.StringVar(value="就绪")

        self._build_ui()
        self.after(200, self._drain_events)
        self.after(500, self.refresh_profiles)

    def _build_ui(self) -> None:
        self._label(self, "AdsPower 环境管理", size=20, bold=True).pack(anchor="w", padx=16, pady=(14, 8))

        settings = self._panel(self)
        settings.pack(fill="x", padx=16, pady=(0, 12))
        for col in range(6):
            settings.grid_columnconfigure(col, weight=1 if col in (1, 3, 5) else 0)

        self._label(settings, "API地址").grid(row=0, column=0, sticky="w", padx=8, pady=8)
        self._entry(settings, self.base_url_var).grid(row=0, column=1, sticky="ew", padx=8, pady=8)
        self._label(settings, "API Key").grid(row=0, column=2, sticky="w", padx=8, pady=8)
        self._entry(settings, self.api_key_var, show="*").grid(row=0, column=3, sticky="ew", padx=8, pady=8)
        self._button(settings, "刷新", self.refresh_profiles, BLUE).grid(row=0, column=4, sticky="ew", padx=8, pady=8)

        self._label(settings, "分组ID").grid(row=1, column=0, sticky="w", padx=8, pady=8)
        self._entry(settings, self.group_id_var).grid(row=1, column=1, sticky="ew", padx=8, pady=8)
        self._label(settings, "网址").grid(row=1, column=2, sticky="w", padx=8, pady=8)
        self._entry(settings, self.url_var).grid(row=1, column=3, sticky="ew", padx=8, pady=8)

        self._label(settings, "代理文件").grid(row=2, column=0, sticky="w", padx=8, pady=8)
        self._entry(settings, self.proxy_file_var).grid(row=2, column=1, columnspan=3, sticky="ew", padx=8, pady=8)
        self._button(settings, "选择代理文件", self.choose_proxy_file).grid(row=2, column=4, sticky="ew", padx=8, pady=8)

        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True, padx=16)
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=2)
        main.grid_rowconfigure(0, weight=1)

        email_panel = self._panel(main)
        email_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        email_panel.grid_rowconfigure(2, weight=1)
        email_panel.grid_columnconfigure(0, weight=1)
        self._label(email_panel, "邮箱导入", size=16, bold=True).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))
        self._label(email_panel, "邮箱只写入环境名称和备注，不自动填写注册页面。", fg=MUTED).grid(
            row=1, column=0, sticky="w", padx=10, pady=(0, 8)
        )
        self.email_list = tk.Listbox(email_panel, selectmode="extended", bg="#ffffff", fg=TEXT, relief="solid")
        self.email_list.grid(row=2, column=0, sticky="nsew", padx=10, pady=8)

        email_buttons = tk.Frame(email_panel, bg=PANEL)
        email_buttons.grid(row=3, column=0, sticky="ew", padx=10, pady=8)
        self._button(email_buttons, "导入邮箱", self.import_emails).pack(side="left")
        self._button(email_buttons, "清空", self.clear_emails).pack(side="left", padx=6)

        create_row = tk.Frame(email_panel, bg=PANEL)
        create_row.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 10))
        self._label(create_row, "空环境数量").pack(side="left")
        self._entry(create_row, self.count_var, width=6).pack(side="left", padx=6)
        tk.Checkbutton(
            create_row,
            text="创建后打开",
            variable=self.open_after_var,
            bg=PANEL,
            fg=TEXT,
            activebackground=PANEL,
        ).pack(side="left")

        create_buttons = tk.Frame(email_panel, bg=PANEL)
        create_buttons.grid(row=5, column=0, sticky="ew", padx=10, pady=(0, 10))
        self._button(create_buttons, "选中邮箱创建", self.create_selected_emails, BLUE).pack(side="left")
        self._button(create_buttons, "全部邮箱创建", self.create_all_emails, BLUE).pack(side="left", padx=6)
        self._button(create_buttons, "创建空环境", self.create_empty_profiles).pack(side="left")

        profile_panel = self._panel(main)
        profile_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        profile_panel.grid_rowconfigure(2, weight=1)
        profile_panel.grid_columnconfigure(0, weight=1)
        self._label(profile_panel, "环境列表", size=16, bold=True).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))

        profile_buttons = tk.Frame(profile_panel, bg=PANEL)
        profile_buttons.grid(row=1, column=0, sticky="ew", padx=10, pady=8)
        self._button(profile_buttons, "刷新", self.refresh_profiles).pack(side="left")
        self._button(profile_buttons, "打开选中", self.open_selected_profiles, BLUE).pack(side="left", padx=6)
        self._button(profile_buttons, "打开全部", self.open_all_profiles, BLUE).pack(side="left")
        self._button(profile_buttons, "删除选中", self.delete_selected_profiles, RED).pack(side="left", padx=6)

        id_row = tk.Frame(profile_panel, bg=PANEL)
        id_row.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 8))
        id_row.grid_columnconfigure(1, weight=1)
        self._label(id_row, "环境ID").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self._entry(id_row, self.profile_ids_var).grid(row=0, column=1, sticky="ew", padx=(0, 6))
        self._button(id_row, "按ID打开", self.open_ids_from_input, BLUE).grid(row=0, column=2, padx=(0, 6))
        self._button(id_row, "按ID删除", self.delete_ids_from_input, RED).grid(row=0, column=3)

        list_frame = tk.Frame(profile_panel, bg=PANEL)
        list_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 10))
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)
        self.profile_list = tk.Listbox(
            list_frame,
            selectmode="extended",
            bg="#ffffff",
            fg=TEXT,
            selectbackground="#bfdbfe",
            selectforeground=TEXT,
            relief="solid",
            font=("Menlo", 12),
            height=14,
        )
        self.profile_list.grid(row=0, column=0, sticky="nsew")
        scrollbar = tk.Scrollbar(list_frame, command=self.profile_list.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.profile_list.configure(yscrollcommand=scrollbar.set)

        self.log_box = tk.Text(self, height=8, bg="#ffffff", fg=TEXT, relief="solid", wrap="word")
        self.log_box.pack(fill="x", padx=16, pady=(12, 6))
        self._label(self, "", textvariable=self.status_var, fg=MUTED).pack(anchor="w", padx=16, pady=(0, 10))

    def _panel(self, parent: tk.Widget) -> tk.Frame:
        return tk.Frame(parent, bg=PANEL, highlightbackground=LINE, highlightthickness=1)

    def _label(
        self,
        parent: tk.Widget,
        text: str,
        size: int = 13,
        bold: bool = False,
        fg: str = TEXT,
        textvariable: Optional[tk.StringVar] = None,
    ) -> tk.Label:
        font = ("Arial", size, "bold" if bold else "normal")
        return tk.Label(parent, text=text, textvariable=textvariable, bg=parent.cget("bg"), fg=fg, font=font)

    def _entry(self, parent: tk.Widget, variable: tk.StringVar, show: Optional[str] = None, width: int = 20) -> tk.Entry:
        return tk.Entry(parent, textvariable=variable, show=show, width=width, bg="#ffffff", fg=TEXT, relief="solid")

    def _button(self, parent: tk.Widget, text: str, command: Any, color: str = "#374151") -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=color,
            fg="#ffffff",
            activebackground=color,
            activeforeground="#ffffff",
            relief="flat",
            padx=10,
            pady=5,
        )

    def choose_proxy_file(self) -> None:
        filename = filedialog.askopenfilename(title="选择代理文件", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if filename:
            self.proxy_file_var.set(filename)

    def import_emails(self) -> None:
        filename = filedialog.askopenfilename(title="导入邮箱", filetypes=[("Email files", "*.txt *.csv"), ("All files", "*.*")])
        if not filename:
            return
        emails = self._read_email_file(Path(filename))
        seen = set(self.emails)
        added = [email for email in emails if email not in seen]
        self.emails.extend(added)
        self._render_emails()
        self.log(f"导入邮箱 {len(added)} 个，当前共 {len(self.emails)} 个")

    def _read_email_file(self, path: Path) -> List[str]:
        text = path.read_text(encoding="utf-8-sig")
        if path.suffix.lower() == ".csv":
            values: List[str] = []
            for row in csv.reader(text.splitlines()):
                values.extend(row)
        else:
            values = text.replace(",", "\n").splitlines()
        return [value.strip() for value in values if "@" in value and value.strip()]

    def clear_emails(self) -> None:
        self.emails = []
        self._render_emails()

    def _render_emails(self) -> None:
        self.email_list.delete(0, tk.END)
        for email in self.emails:
            self.email_list.insert(tk.END, email)

    def _config(self) -> Dict[str, str]:
        return {
            "base_url": self.base_url_var.get().strip() or DEFAULT_BASE_URL,
            "api_key": self.api_key_var.get().strip(),
            "group_id": self.group_id_var.get().strip() or "0",
            "target_url": self.url_var.get().strip() or DEFAULT_TARGET_URL,
            "proxy_file": self.proxy_file_var.get().strip() or DEFAULT_PROXY_FILE,
        }

    def create_selected_emails(self) -> None:
        emails = [self.emails[i] for i in self.email_list.curselection()]
        if not emails:
            messagebox.showinfo("提示", "请先选择邮箱")
            return
        self._run("创建环境", self._create_worker, self._config(), emails)

    def create_all_emails(self) -> None:
        if not self.emails:
            messagebox.showinfo("提示", "请先导入邮箱")
            return
        self._run("创建环境", self._create_worker, self._config(), list(self.emails))

    def create_empty_profiles(self) -> None:
        try:
            count = max(1, int(self.count_var.get()))
        except ValueError:
            count = 1
        self._run("创建环境", self._create_worker, self._config(), [None] * count)

    def refresh_profiles(self) -> None:
        self._run("刷新列表", self._refresh_worker, self._config())

    def open_selected_profiles(self) -> None:
        ids = self._selected_profile_ids()
        if not ids:
            messagebox.showinfo("提示", "请先选择环境")
            return
        self._run("打开环境", self._open_worker, self._config(), ids)

    def open_all_profiles(self) -> None:
        ids = [profile.get("user_id") for profile in self.profiles if profile.get("user_id")]
        if not ids:
            messagebox.showinfo("提示", "当前列表没有环境，先刷新一下")
            return
        self._run("打开环境", self._open_worker, self._config(), ids)

    def open_ids_from_input(self) -> None:
        ids = self._ids_from_input()
        if not ids:
            messagebox.showinfo("提示", "请先输入环境ID，多个ID用逗号或空格分隔")
            return
        self._run("打开环境", self._open_worker, self._config(), ids)

    def delete_selected_profiles(self) -> None:
        ids = self._selected_profile_ids()
        if not ids:
            messagebox.showinfo("提示", "请先选择环境")
            return
        if not messagebox.askyesno("确认删除", f"确认删除 {len(ids)} 个环境？"):
            return
        self._run("删除环境", self._delete_worker, self._config(), ids)

    def delete_ids_from_input(self) -> None:
        ids = self._ids_from_input()
        if not ids:
            messagebox.showinfo("提示", "请先输入环境ID，多个ID用逗号或空格分隔")
            return
        if not messagebox.askyesno("确认删除", f"确认删除 {len(ids)} 个环境？"):
            return
        self._run("删除环境", self._delete_worker, self._config(), ids)

    def _selected_profile_ids(self) -> List[str]:
        ids = []
        for index in self.profile_list.curselection():
            profile_index = index - 2
            if profile_index < 0 or profile_index >= len(self.profiles):
                continue
            profile = self.profiles[profile_index]
            if profile.get("user_id"):
                ids.append(profile["user_id"])
        return ids

    def _ids_from_input(self) -> List[str]:
        raw = self.profile_ids_var.get().replace(",", " ").strip()
        return [part.strip() for part in raw.split() if part.strip()]

    def _create_worker(self, cfg: Dict[str, str], emails: List[Optional[str]]) -> None:
        check_connection(cfg["base_url"], cfg["api_key"])
        proxies = load_proxies(cfg["proxy_file"])
        for index, email in enumerate(emails, start=1):
            label = email or f"no-email-{index}"
            proxy = random.choice(proxies) if proxies else None
            profile_id = create_profile(
                cfg["base_url"],
                cfg["api_key"],
                cfg["group_id"],
                cfg["target_url"],
                f"ChatGPT - {label}",
                proxy,
                account_email=email,
            )
            self.events.put(("log", f"已创建 {profile_id}：{label}"))
            time.sleep(1.1)
            if self.open_after_var.get():
                started = open_profile(cfg["base_url"], cfg["api_key"], profile_id)
                debug_port = str(started.get("data", {}).get("debug_port") or "")
                open_url_by_debug_port(debug_port, cfg["target_url"])
                self.events.put(("log", f"已打开 {profile_id}"))
                time.sleep(1.1)
        self._refresh_worker(cfg)

    def _refresh_worker(self, cfg: Dict[str, str]) -> None:
        check_connection(cfg["base_url"], cfg["api_key"])
        response = request_json("GET", cfg["base_url"], "/api/v1/user/list?page=1&page_size=100", api_key=cfg["api_key"])
        self.events.put(("profiles", response.get("data", {}).get("list", [])))

    def _open_worker(self, cfg: Dict[str, str], profile_ids: List[str]) -> None:
        check_connection(cfg["base_url"], cfg["api_key"])
        for profile_id in profile_ids:
            started = open_profile(cfg["base_url"], cfg["api_key"], profile_id)
            debug_port = str(started.get("data", {}).get("debug_port") or "")
            open_url_by_debug_port(debug_port, cfg["target_url"])
            self.events.put(("log", f"已打开 {profile_id}"))
            time.sleep(1.1)

    def _delete_worker(self, cfg: Dict[str, str], profile_ids: List[str]) -> None:
        check_connection(cfg["base_url"], cfg["api_key"])
        request_json("POST", cfg["base_url"], "/api/v1/user/delete", {"user_ids": profile_ids}, cfg["api_key"])
        self.events.put(("log", f"已删除 {len(profile_ids)} 个环境"))
        self._refresh_worker(cfg)

    def _run(self, label: str, func: Any, *args: Any) -> None:
        self.status_var.set(f"{label}运行中...")
        threading.Thread(target=self._worker_wrapper, args=(func, args), daemon=True).start()

    def _worker_wrapper(self, func: Any, args: tuple[Any, ...]) -> None:
        try:
            func(*args)
            self.events.put(("status", "就绪"))
        except AdsPowerError as exc:
            self.events.put(("error", str(exc)))
            self.events.put(("status", "出错"))
        except Exception as exc:
            self.events.put(("error", f"Unexpected error: {exc}"))
            self.events.put(("status", "出错"))

    def _drain_events(self) -> None:
        while True:
            try:
                kind, payload = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "log":
                self.log(str(payload))
            elif kind == "profiles":
                self.profiles = list(payload)
                self._render_profiles()
                self.log(f"刷新完成，共 {len(self.profiles)} 个环境")
            elif kind == "status":
                self.status_var.set(str(payload))
            elif kind == "error":
                self.log(f"错误：{payload}")
                messagebox.showerror("错误", str(payload))
        self.after(200, self._drain_events)

    def _render_profiles(self) -> None:
        self.profile_list.delete(0, tk.END)
        self.profile_list.insert(tk.END, "序号 | 环境ID   | 名称 | 邮箱备注 | 代理")
        self.profile_list.insert(tk.END, "-" * 96)
        for profile in self.profiles:
            proxy = profile.get("user_proxy_config") or {}
            remark = profile.get("remark") or ""
            email = remark.replace("email:", "").strip() if remark.startswith("email:") else remark
            proxy_text = ""
            if proxy.get("proxy_host"):
                proxy_text = f"{proxy.get('proxy_type', '')}://{proxy.get('proxy_host')}:{proxy.get('proxy_port')}"
            line = (
                f"{profile.get('serial_number', '')} | {profile.get('user_id', '')} | "
                f"{profile.get('name', '')} | {email} | {proxy_text}"
            )
            self.profile_list.insert(tk.END, line)

    def log(self, message: str) -> None:
        self.log_box.insert(tk.END, f"{time.strftime('%H:%M:%S')}  {message}\n")
        self.log_box.see(tk.END)


if __name__ == "__main__":
    AdsPowerGui().mainloop()
