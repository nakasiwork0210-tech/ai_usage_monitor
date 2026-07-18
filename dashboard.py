# -*- coding: utf-8 -*-
"""利用量ダッシュボードウィンドウ。

トレイメニューの「ダッシュボードを開く」から別プロセスとして起動される。
上段: 各プロバイダの利用量メーター + リセットカウントダウン + 追加情報
下段: ローカルコストスキャンの日次チャート (Today / 7d / 30d 切り替え)
テーマ: 自動 (Windows 設定に追従) / ライト / ダーク をボタンで切り替え。
"""

import ctypes
import threading
import tkinter as tk
from datetime import datetime

import common
import localcost
import providers

THEME_LABELS = {"auto": "テーマ: 自動", "light": "テーマ: ライト", "dark": "テーマ: ダーク"}
THEME_CYCLE = {"auto": "light", "light": "dark", "dark": "auto"}


class Dashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Usage Monitor")
        self.geometry("640x640")
        self.minsize(560, 520)
        self.cfg = common.load_config()
        self.T = common.THEMES[common.resolve_theme(self.cfg)]
        self.period = tk.IntVar(value=7)
        self.cost_data = None
        self.last_states = []
        self._build_ui()
        self.after(50, self._apply_titlebar)
        self.refresh()

    # ------------------------------------------------------------ UI 構築
    def _build_ui(self):
        T = self.T
        self.configure(bg=T["bg"])
        for child in self.winfo_children():
            child.destroy()

        font = ("Yu Gothic UI", 9)
        top = tk.Frame(self, bg=T["bg"])
        top.pack(fill="x", padx=16, pady=(12, 4))
        tk.Label(top, text="利用量ダッシュボード", bg=T["bg"], fg=T["fg"],
                 font=("Yu Gothic UI", 14, "bold")).pack(side="left")
        self.refresh_btn = tk.Button(top, text="更新", command=self.refresh,
                                     bg=T["bar_bg"], fg=T["fg"], relief="flat", padx=12)
        self.refresh_btn.pack(side="right")
        self.theme_btn = tk.Button(top, text=THEME_LABELS[self.cfg.get("theme", "auto")],
                                   command=self.cycle_theme,
                                   bg=T["bar_bg"], fg=T["fg"], relief="flat", padx=10)
        self.theme_btn.pack(side="right", padx=6)
        self.status = tk.Label(top, text="", bg=T["bg"], fg=T["dim"], font=font)
        self.status.pack(side="right", padx=8)

        self.meters = tk.Frame(self, bg=T["bg"])
        self.meters.pack(fill="x", padx=16, pady=4)

        sel = tk.Frame(self, bg=T["bg"])
        sel.pack(fill="x", padx=16, pady=(10, 0))
        tk.Label(sel, text="ローカルコスト", bg=T["bg"], fg=T["fg"],
                 font=("Yu Gothic UI", 11, "bold")).pack(side="left")
        for label, days in (("Today", 1), ("7d", 7), ("30d", 30)):
            tk.Radiobutton(sel, text=label, value=days, variable=self.period,
                           command=self.draw_charts, bg=T["bg"], fg=T["fg"],
                           selectcolor=T["bar_bg"],
                           activebackground=T["bg"], activeforeground=T["fg"],
                           font=font).pack(side="left", padx=4)

        self.chart = tk.Canvas(self, bg=T["bg"], highlightthickness=0)
        self.chart.pack(fill="both", expand=True, padx=16, pady=8)
        self.chart.bind("<Configure>", lambda e: self.draw_charts())

        self.totals = tk.Label(self, text="", bg=T["bg"], fg=T["fg"],
                               font=("Yu Gothic UI", 10), justify="left", anchor="w")
        self.totals.pack(fill="x", padx=16, pady=(0, 12))

    def _apply_titlebar(self):
        """Windows のタイトルバーをテーマに合わせる (DWMWA_USE_IMMERSIVE_DARK_MODE)。"""
        try:
            self.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            dark = ctypes.c_int(0 if self.T is common.THEMES["light"] else 1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark), 4)
            # 再描画を促す
            self.withdraw()
            self.deiconify()
        except Exception:
            pass

    def cycle_theme(self):
        self.cfg["theme"] = THEME_CYCLE[self.cfg.get("theme", "auto")]
        common.save_config(self.cfg)
        self.T = common.THEMES[common.resolve_theme(self.cfg)]
        self._build_ui()
        self._apply_titlebar()
        self._rebuild_meters()
        self.draw_charts()
        if self.last_states:
            self._set_status()

    def sev_color(self, pct):
        if pct is None:
            return self.T["dim"]
        if pct >= 90:
            return self.T["red"]
        if pct >= 70:
            return self.T["yellow"]
        return self.T["green"]

    # ------------------------------------------------------------ 取得
    def refresh(self):
        self.status.config(text="取得中...")
        self.refresh_btn.config(state="disabled")
        threading.Thread(target=self._fetch, daemon=True).start()

    def _fetch(self):
        states = [cls().fetch() for cls in providers.PROVIDERS]
        cost = localcost.scan(30)
        self.after(0, lambda: self._apply(states, cost))

    def _apply(self, states, cost):
        self.cost_data = cost
        self.last_states = states
        self._rebuild_meters()
        self.draw_charts()
        self._set_status()
        self.refresh_btn.config(state="normal")

    def _set_status(self):
        self.status.config(text="更新: " + datetime.now().strftime("%H:%M:%S"))

    def _rebuild_meters(self):
        for child in self.meters.winfo_children():
            child.destroy()
        for st in self.last_states:
            self._build_provider(st)

    def _build_provider(self, st):
        T = self.T
        frame = tk.Frame(self.meters, bg=T["bg"])
        frame.pack(fill="x", pady=4)
        head = f"{st.name}" + (f"  ({st.plan})" if st.plan else "")
        tk.Label(frame, text=head, bg=T["bg"], fg=T["fg"],
                 font=("Yu Gothic UI", 11, "bold")).pack(anchor="w")
        if st.error:
            tk.Label(frame, text="⚠ " + st.error, bg=T["bg"], fg=T["red"],
                     font=("Yu Gothic UI", 10)).pack(anchor="w", padx=12)
            return
        for w in st.windows:
            row = tk.Frame(frame, bg=T["bg"])
            row.pack(fill="x", padx=12, pady=2)
            tk.Label(row, text=w.label, bg=T["bg"], fg=T["fg"], width=9, anchor="w",
                     font=("Yu Gothic UI", 9)).pack(side="left")
            bar = tk.Canvas(row, height=14, width=220, bg=T["bar_bg"], highlightthickness=0)
            bar.pack(side="left", padx=6)
            pct = w.percent or 0
            bar.create_rectangle(0, 0, 220 * min(pct, 100) / 100, 14,
                                 fill=self.sev_color(w.percent), width=0)
            info = f"{pct:.0f}%"
            if w.reset_dt:
                info += f"  リセット {providers.fmt_reset(w.reset_dt)} ({providers.fmt_countdown(w.reset_dt)})"
            tk.Label(row, text=info, bg=T["bg"], fg=T["dim"],
                     font=("Yu Gothic UI", 9)).pack(side="left")
        for line in st.extras:
            tk.Label(frame, text="· " + line, bg=T["bg"], fg=T["dim"],
                     font=("Yu Gothic UI", 9)).pack(anchor="w", padx=12)

    # ------------------------------------------------------------ チャート
    def draw_charts(self):
        c = self.chart
        c.delete("all")
        if not self.cost_data:
            return
        days = self.period.get()
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 50 or h < 50:
            return
        half = h // 2
        claude = localcost.series(self.cost_data["claude"], days)
        codex = localcost.series(self.cost_data["codex"], days)
        self._bars(c, 0, 0, w, half - 8, claude, self.T["blue"],
                   "Claude (コスト USD 換算)", lambda v: f"${v:.2f}", idx=1)
        self._bars(c, 0, half + 8, w, half - 8, codex, self.T["peach"],
                   "Codex (トークン)", self._fmt_tokens, idx=2)
        self._totals(claude, codex, days)

    @staticmethod
    def _fmt_tokens(v):
        if v >= 1_000_000:
            return f"{v / 1_000_000:.1f}M"
        if v >= 1_000:
            return f"{v / 1_000:.0f}K"
        return f"{v:.0f}"

    def _bars(self, c, x0, y0, w, h, data, color, title, fmt, idx):
        T = self.T
        c.create_text(x0 + 4, y0 + 8, text=title, fill=T["fg"], anchor="w",
                      font=("Yu Gothic UI", 9, "bold"))
        top = y0 + 24
        bottom = y0 + h - 18
        if bottom <= top:
            return
        vals = [d[idx] for d in data]
        vmax = max(vals) or 1
        n = len(data)
        gap = 2 if n > 10 else 6
        bw = max(3, (w - gap * (n + 1)) // n)
        show_labels = n <= 7
        for i, item in enumerate(data):
            v = item[idx]
            x = x0 + gap + i * (bw + gap)
            bh = int((bottom - top) * v / vmax)
            if bh > 0:
                c.create_rectangle(x, bottom - bh, x + bw, bottom, fill=color, width=0)
            else:
                c.create_line(x, bottom, x + bw, bottom, fill=T["bar_bg"])
            if show_labels:
                c.create_text(x + bw / 2, bottom + 9, text=item[0], fill=T["dim"],
                              font=("Yu Gothic UI", 8))
                if v > 0:
                    c.create_text(x + bw / 2, bottom - bh - 8, text=fmt(v), fill=T["fg"],
                                  font=("Yu Gothic UI", 8))
            elif i == 0 or i == n - 1:
                c.create_text(x + bw / 2, bottom + 9, text=item[0], fill=T["dim"],
                              font=("Yu Gothic UI", 8))

    def _totals(self, claude, codex, days):
        c_cost = sum(d[1] for d in claude)
        c_tok = sum(d[2] for d in claude)
        x_cost = sum(d[1] for d in codex)
        x_tok = sum(d[2] for d in codex)
        label = {1: "今日", 7: "直近7日", 30: "直近30日"}[days]
        self.totals.config(text=(
            f"{label}合計 — Claude: ${c_cost:.2f} ({self._fmt_tokens(c_tok)} tok)  /  "
            f"Codex: {self._fmt_tokens(x_tok)} tok (gpt-5換算 ≈ ${x_cost:.2f})"
        ))


if __name__ == "__main__":
    Dashboard().mainloop()
