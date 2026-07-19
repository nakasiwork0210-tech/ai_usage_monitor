# -*- coding: utf-8 -*-
"""
Usage Monitor — Claude Code / Codex (ChatGPT) の利用量を Windows タスクトレイに表示する常駐アプリ。

各 CLI がローカルに保存している OAuth 認証情報 (~/.claude/.credentials.json,
~/.codex/auth.json) をそのまま利用し、各サービスの公式利用量エンドポイントを
呼び出して残量を取得する。追加のログインやトークンのコピーは行わない。

使い方:
  pythonw usage_monitor.py          トレイ常駐
  python usage_monitor.py --cli     利用量をテキスト表示して終了
  python usage_monitor.py --json    利用量を JSON 表示して終了
  python usage_monitor.py --cost 7  ローカルコスト集計 (直近7日) を表示して終了
"""

import argparse
import ctypes
import json
import logging
import os
import subprocess
import sys
import threading
from datetime import datetime

import common
import providers
from common import APP_DIR, FROZEN, load_config, save_config
from providers import ProviderState

APP_NAME = "UsageMonitor"
LOG_PATH = os.path.join(APP_DIR, "usage_monitor.log")

logging.basicConfig(
    filename=LOG_PATH, level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s", encoding="utf-8",
)
log = logging.getLogger(APP_NAME)


# ---------------------------------------------------------------- CLI

def run_cli(as_json=False):
    states = [cls().fetch() for cls in providers.PROVIDERS]
    if as_json:
        print(json.dumps([st.to_dict() for st in states], ensure_ascii=False, indent=2))
        return
    for st in states:
        plan = f" ({st.plan})" if st.plan else ""
        print(f"== {st.name}{plan} ==")
        if st.error:
            print(f"  !! {st.error}")
            continue
        for w in st.windows:
            print("  " + w.text())
        for line in st.extras:
            print("  - " + line)


def run_cost(days):
    import localcost
    data = localcost.scan(max(days, 1))
    for name, key in (("Claude", "claude"), ("Codex", "codex")):
        rows = localcost.series(data[key], days)
        total_cost = sum(r[1] for r in rows)
        total_tok = sum(r[2] for r in rows)
        print(f"== {name} (直近{days}日) ==")
        for label, cost, tok in rows:
            if cost or tok:
                print(f"  {label}  ${cost:8.2f}  {tok:>12,} tok")
        print(f"  合計   ${total_cost:8.2f}  {total_tok:>12,} tok")


# ---------------------------------------------------------------- トレイ UI

def severity_color(pct):
    if pct is None:
        return (128, 128, 128, 255)
    if pct >= 90:
        return (229, 77, 66, 255)    # 赤
    if pct >= 70:
        return (240, 173, 45, 255)   # 黄
    return (72, 199, 116, 255)       # 緑


def _load_font(size):
    from PIL import ImageFont
    for name in ("arialbd.ttf", "arial.ttf", "segoeui.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def draw_icon(states, cfg):
    """設定に応じてアイコンを描画。both=縦バー2本 / 単独・auto=1本+%数字。
    枠線の色はタスクバーの明暗に合わせる。"""
    from PIL import Image, ImageDraw
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    mode = cfg.get("icon_mode", "both")
    outline = (80, 80, 80, 255) if common.taskbar_is_light() else (150, 150, 150, 255)

    def bar(x, bar_w, st):
        pct = st.worst_percent() if st else None
        d.rounded_rectangle([x, 2, x + bar_w, size - 2], radius=6,
                            outline=outline, width=3)
        if st and st.error:
            d.line([x + 5, size // 2 - 8, x + bar_w - 5, size // 2 + 8],
                   fill=(229, 77, 66, 255), width=4)
            d.line([x + 5, size // 2 + 8, x + bar_w - 5, size // 2 - 8],
                   fill=(229, 77, 66, 255), width=4)
        elif pct is not None:
            h = int((size - 10) * min(pct, 100) / 100)
            if h > 0:
                d.rounded_rectangle([x + 3, size - 5 - h, x + bar_w - 3, size - 5],
                                    radius=3, fill=severity_color(pct))

    if mode == "both":
        bar(6, 22, states[0] if states else None)
        bar(size - 6 - 22, 22, states[1] if len(states) > 1 else None)
        return img

    if mode == "claude":
        st = states[0] if states else None
    elif mode == "codex":
        st = states[1] if len(states) > 1 else None
    else:  # auto: 使用率が最も高いプロバイダ
        st = max((s for s in states if s.worst_percent() is not None),
                 key=lambda s: s.worst_percent(), default=states[0] if states else None)

    if st is None:
        return img
    if cfg.get("icon_percent") and not st.error and st.worst_percent() is not None:
        pct = st.worst_percent()
        text = f"{pct:.0f}"
        font = _load_font(40 if len(text) < 3 else 30)
        bbox = d.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        d.text(((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1]),
               text, font=font, fill=severity_color(pct))
    else:
        bar((size - 30) // 2, 30, st)
    return img


class App:
    def __init__(self):
        import pystray
        self.pystray = pystray
        self.cfg = load_config()
        self.providers = [cls() for cls in providers.PROVIDERS]
        self.states = [ProviderState(p.name) for p in self.providers]
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.notified = set()
        self.icon = pystray.Icon(APP_NAME, draw_icon(self.states, self.cfg), APP_NAME,
                                 menu=self.build_menu())

    # ---- メニュー ----
    def build_menu(self):
        ps = self.pystray
        items = [ps.MenuItem("ダッシュボードを開く", self.on_dashboard, default=True),
                 ps.Menu.SEPARATOR]
        for idx in range(len(self.providers)):
            items.append(ps.MenuItem(self.header_text(idx), None, enabled=False))
            for widx in range(6):
                items.append(ps.MenuItem(self.window_text(idx, widx), None,
                                         enabled=False,
                                         visible=self.window_visible(idx, widx)))
            for eidx in range(4):
                items.append(ps.MenuItem(self.extra_text(idx, eidx), None,
                                         enabled=False,
                                         visible=self.extra_visible(idx, eidx)))
            items.append(ps.Menu.SEPARATOR)

        def mode_item(label, mode):
            return ps.MenuItem(label, lambda i1, i2: self.set_mode(mode),
                               radio=True,
                               checked=lambda item: self.cfg.get("icon_mode") == mode)

        display = ps.Menu(
            mode_item("両方 (バー2本)", "both"),
            mode_item("Claude のみ", "claude"),
            mode_item("Codex のみ", "codex"),
            mode_item("自動 (使用率最高)", "auto"),
            ps.Menu.SEPARATOR,
            ps.MenuItem("%数字で表示 (単独時)", self.on_toggle_percent,
                        checked=lambda item: bool(self.cfg.get("icon_percent"))),
        )

        def theme_item(label, mode):
            return ps.MenuItem(label, lambda i1, i2: self.set_theme(mode),
                               radio=True,
                               checked=lambda item: self.cfg.get("theme", "auto") == mode)

        theme = ps.Menu(
            theme_item("自動 (Windows 設定に追従)", "auto"),
            theme_item("ライト", "light"),
            theme_item("ダーク", "dark"),
        )
        items += [
            ps.MenuItem(self.updated_text(), None, enabled=False),
            ps.MenuItem("今すぐ更新", self.on_refresh),
            ps.MenuItem("アイコン表示", display),
            ps.MenuItem("テーマ (ダッシュボード)", theme),
            ps.MenuItem("Windows 起動時に自動開始", self.on_toggle_autostart,
                        checked=lambda item: autostart_enabled()),
            ps.MenuItem("終了", self.on_quit),
        ]
        return ps.Menu(*items)

    def header_text(self, idx):
        def text(item):
            st = self.states[idx]
            if st.error:
                return f"{st.name}: ⚠ {st.error}"
            plan = f" ({st.plan})" if st.plan else ""
            return f"{st.name}{plan}"
        return text

    def window_text(self, idx, widx):
        def text(item):
            st = self.states[idx]
            return "    " + st.windows[widx].text() if widx < len(st.windows) else ""
        return text

    def window_visible(self, idx, widx):
        return lambda item: widx < len(self.states[idx].windows)

    def extra_text(self, idx, eidx):
        def text(item):
            st = self.states[idx]
            return "    · " + st.extras[eidx] if eidx < len(st.extras) else ""
        return text

    def extra_visible(self, idx, eidx):
        return lambda item: eidx < len(self.states[idx].extras)

    def updated_text(self):
        def text(item):
            times = [st.updated for st in self.states if st.updated]
            return "更新: " + max(times).strftime("%H:%M:%S") if times else "未取得"
        return text

    # ---- アクション ----
    def on_dashboard(self, icon, item):
        try:
            if FROZEN:
                subprocess.Popen([sys.executable, "--dashboard"], cwd=APP_DIR)
            else:
                pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
                exe = pyw if os.path.exists(pyw) else sys.executable
                subprocess.Popen([exe, os.path.join(APP_DIR, "dashboard.py")], cwd=APP_DIR)
        except Exception as e:
            log.error("dashboard launch failed: %r", e)

    def on_refresh(self, icon, item):
        threading.Thread(target=self.refresh, daemon=True).start()

    def set_mode(self, mode):
        self.cfg["icon_mode"] = mode
        save_config(self.cfg)
        self.redraw()

    def set_theme(self, mode):
        self.cfg["theme"] = mode
        save_config(self.cfg)
        self.icon.update_menu()

    def on_toggle_percent(self, icon, item):
        self.cfg["icon_percent"] = not self.cfg.get("icon_percent")
        save_config(self.cfg)
        self.redraw()

    def on_toggle_autostart(self, icon, item):
        set_autostart(not autostart_enabled())

    def on_quit(self, icon, item):
        self.stop_event.set()
        icon.stop()

    # ---- 更新処理 ----
    def redraw(self):
        self.icon.icon = draw_icon(self.states, self.cfg)
        self.icon.title = self.tooltip()
        self.icon.update_menu()

    def refresh(self):
        if not self.lock.acquire(blocking=False):
            return
        try:
            for i, p in enumerate(self.providers):
                st = p.fetch()
                self.states[i] = st
                self.check_notify(st)
            self.redraw()
        except Exception as e:
            log.exception("refresh failed: %r", e)
        finally:
            self.lock.release()

    def tooltip(self):
        parts = []
        for st in self.states:
            if st.error:
                parts.append(f"{st.name}: ⚠")
            else:
                pct = st.worst_percent()
                parts.append(f"{st.name}: {pct:.0f}%" if pct is not None else f"{st.name}: —")
        return " / ".join(parts)[:127]

    def check_notify(self, st):
        th = self.cfg.get("notify_threshold", 90)
        for w in st.windows:
            key = (st.name, w.label)
            if w.percent is not None and w.percent >= th:
                if key not in self.notified:
                    self.notified.add(key)
                    try:
                        self.icon.notify(f"{w.label}ウィンドウが {w.percent:.0f}% に達しました",
                                         f"{st.name} 利用量")
                    except Exception:
                        pass
            else:
                self.notified.discard(key)

    def loop(self):
        interval = max(1, int(self.cfg.get("refresh_minutes", 5))) * 60
        while not self.stop_event.wait(0.5):
            self.refresh()
            if self.stop_event.wait(interval):
                break

    def run(self):
        threading.Thread(target=self.loop, daemon=True).start()
        self.icon.run()


# ---------------------------------------------------------------- 自動起動

STARTUP_VBS = os.path.join(
    os.environ.get("APPDATA", ""),
    r"Microsoft\Windows\Start Menu\Programs\Startup", "usage_monitor.vbs")


def autostart_enabled():
    return os.path.exists(STARTUP_VBS)


def set_autostart(enable):
    try:
        if enable:
            if FROZEN:
                cmd = f'"""{sys.executable}"""'
            else:
                pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
                if not os.path.exists(pyw):
                    pyw = sys.executable
                cmd = f'"""{pyw}"" ""{os.path.abspath(__file__)}"""'
            with open(STARTUP_VBS, "w", encoding="utf-8") as f:
                f.write(f'CreateObject("WScript.Shell").Run {cmd}, 0, False\n')
            log.info("autostart enabled")
        else:
            if os.path.exists(STARTUP_VBS):
                os.remove(STARTUP_VBS)
            log.info("autostart disabled")
    except Exception as e:
        log.error("autostart toggle failed: %r", e)


def already_running():
    ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\UsageMonitorMutex")
    return ctypes.windll.kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS


def main():
    parser = argparse.ArgumentParser(description="Claude / Codex usage monitor")
    parser.add_argument("--cli", action="store_true", help="利用量をテキスト表示して終了")
    parser.add_argument("--json", action="store_true", help="利用量を JSON 表示して終了")
    parser.add_argument("--cost", type=int, nargs="?", const=7, metavar="DAYS",
                        help="ローカルコスト集計を表示して終了 (既定: 7日)")
    parser.add_argument("--dashboard", action="store_true",
                        help="ダッシュボードウィンドウを直接開く")
    args = parser.parse_args()

    if args.dashboard:
        import dashboard
        dashboard.Dashboard().mainloop()
        return

    if args.cli or args.json:
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
        run_cli(as_json=args.json)
        return
    if args.cost is not None:
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
        run_cost(args.cost)
        return

    if already_running():
        log.info("already running; exit")
        return
    App().run()


if __name__ == "__main__":
    main()
