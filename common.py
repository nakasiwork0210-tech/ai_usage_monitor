# -*- coding: utf-8 -*-
"""設定ファイル IO とテーマ定義(トレイ・ダッシュボード共通)。"""

import json
import os
import sys

FROZEN = getattr(sys, "frozen", False)  # PyInstaller ビルドかどうか
APP_DIR = os.path.dirname(sys.executable if FROZEN else os.path.abspath(__file__))
CONFIG_PATH = os.path.join(APP_DIR, "config.json")

DEFAULT_CONFIG = {
    "refresh_minutes": 5,
    "notify_threshold": 90,
    "icon_mode": "both",    # both | claude | codex | auto
    "icon_percent": False,  # 単独表示時に%数字を描く
    "theme": "auto",        # auto | light | dark
}


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


def save_config(cfg):
    try:
        tmp = CONFIG_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        os.replace(tmp, CONFIG_PATH)
    except Exception:
        pass


# ---------------------------------------------------------------- テーマ

THEMES = {
    "dark": {
        "bg": "#1e1e2e", "fg": "#cdd6f4", "dim": "#7f849c", "bar_bg": "#313244",
        "green": "#a6e3a1", "yellow": "#f9e2af", "red": "#f38ba8",
        "blue": "#89b4fa", "peach": "#fab387",
    },
    "light": {
        "bg": "#f5f5f7", "fg": "#1c1c27", "dim": "#6c6f85", "bar_bg": "#e0e0e6",
        "green": "#40a02b", "yellow": "#df8e1d", "red": "#d20f39",
        "blue": "#1e66f5", "peach": "#fe640b",
    },
}


def _reg_light(value_name):
    """Windows のテーマ設定 (1=ライト)。読めなければ None。"""
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as key:
            return bool(winreg.QueryValueEx(key, value_name)[0])
    except Exception:
        return None


def apps_use_light():
    v = _reg_light("AppsUseLightTheme")
    return True if v is None else v


def taskbar_is_light():
    v = _reg_light("SystemUsesLightTheme")
    return False if v is None else v  # 既定のタスクバーはダーク


def resolve_theme(cfg):
    """config の theme 設定 → 'dark' か 'light'。"""
    mode = cfg.get("theme", "auto")
    if mode in ("dark", "light"):
        return mode
    return "light" if apps_use_light() else "dark"
