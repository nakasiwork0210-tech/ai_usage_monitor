# -*- coding: utf-8 -*-
"""Claude / Codex の利用量 API プロバイダと共通ヘルパー。"""

import json
import logging
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

APP_NAME = "UsageMonitor"
HOME = os.path.expanduser("~")

CLAUDE_CRED_PATH = os.path.join(HOME, ".claude", ".credentials.json")
CLAUDE_CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"  # Claude Code 公式 OAuth クライアント
CODEX_AUTH_PATH = os.path.join(os.environ.get("CODEX_HOME", os.path.join(HOME, ".codex")), "auth.json")
CODEX_CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"  # Codex CLI 公式 OAuth クライアント

log = logging.getLogger(APP_NAME)


def http_json(url, headers=None, payload=None, method=None, timeout=20):
    """JSON を送受信する小さなヘルパー。(status, body_or_text) を返す。"""
    data = json.dumps(payload).encode() if payload is not None else None
    h = {"User-Agent": f"{APP_NAME}/1.0"}
    if data is not None:
        h["Content-Type"] = "application/json"
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            text = e.read().decode()[:500]
        except Exception:
            text = ""
        return e.code, text
    except Exception as e:
        return None, repr(e)


def atomic_write_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f)
    os.replace(tmp, path)


def parse_reset_dt(value):
    """resets_at (ISO8601 文字列 or epoch秒) → ローカル datetime。"""
    try:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value)
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone().replace(tzinfo=None)
    except Exception:
        return None


def fmt_countdown(dt):
    """リセット時刻までの残り時間 → 「あと◯◯」表記。"""
    if dt is None:
        return ""
    secs = (dt - datetime.now()).total_seconds()
    if secs <= 0:
        return "まもなく"
    mins = int(secs // 60)
    if mins < 60:
        return f"あと{mins}分"
    hours, mins = divmod(mins, 60)
    if hours < 24:
        return f"あと{hours}時間{mins}分"
    days, hours = divmod(hours, 24)
    return f"あと{days}日{hours}時間"


def fmt_reset(dt):
    if dt is None:
        return ""
    if dt.date() == datetime.now().date():
        return dt.strftime("%H:%M")
    return dt.strftime("%m/%d %H:%M")


class Window:
    """1 つの利用量ウィンドウ(5h / 週 など)。"""

    def __init__(self, label, percent, reset_dt=None):
        self.label = label
        self.percent = percent  # 0-100 or None
        self.reset_dt = reset_dt

    def text(self):
        if self.percent is None:
            return f"{self.label}: —"
        s = f"{self.label}: {self.percent:.0f}%"
        if self.reset_dt:
            s += f" (リセット {fmt_reset(self.reset_dt)} / {fmt_countdown(self.reset_dt)})"
        return s


class ProviderState:
    def __init__(self, name):
        self.name = name
        self.windows = []      # list[Window]
        self.extras = []       # 追加情報の表示行 (クレジット等)
        self.error = None      # 表示用エラーメッセージ
        self.plan = ""
        self.updated = None    # datetime

    def worst_percent(self):
        vals = [w.percent for w in self.windows if w.percent is not None]
        return max(vals) if vals else None

    def to_dict(self):
        return {
            "name": self.name,
            "plan": self.plan,
            "error": self.error,
            "updated": self.updated.isoformat() if self.updated else None,
            "windows": [
                {"label": w.label, "percent": w.percent,
                 "reset": w.reset_dt.isoformat() if w.reset_dt else None}
                for w in self.windows
            ],
            "extras": self.extras,
        }


# ---------------------------------------------------------------- Claude

class ClaudeProvider:
    name = "Claude"

    def fetch(self):
        st = ProviderState(self.name)
        try:
            with open(CLAUDE_CRED_PATH, encoding="utf-8") as f:
                data = json.load(f)
            cred = data["claudeAiOauth"]
        except Exception as e:
            st.error = "認証ファイルなし (claude /login)"
            log.warning("claude creds: %r", e)
            return st

        # 期限切れなら先にリフレッシュ
        if cred.get("expiresAt", 0) / 1000 < time.time() + 60:
            if not self._refresh(data, cred, st):
                return st

        status, body = self._usage(cred)
        if status == 401:
            # 期限内でも失効していることがある → リフレッシュして 1 回だけ再試行
            if not self._refresh(data, cred, st):
                return st
            status, body = self._usage(cred)

        if status != 200 or not isinstance(body, dict):
            st.error = f"取得失敗 ({status})"
            log.warning("claude usage %s: %s", status, str(body)[:300])
            return st

        st.plan = str(body.get("subscriptionType") or body.get("rate_limit_tier") or "")
        labels = [
            ("five_hour", "5時間"),
            ("seven_day", "週"),
            ("seven_day_sonnet", "週 Sonnet"),
            ("seven_day_opus", "週 Opus"),
        ]
        for key, label in labels:
            v = body.get(key)
            if isinstance(v, dict):
                pct = v.get("utilization")
                st.windows.append(Window(label, float(pct) if pct is not None else None,
                                         parse_reset_dt(v.get("resets_at"))))
        extra = body.get("extra_usage")
        if isinstance(extra, dict) and extra.get("limit"):
            st.extras.append(f"追加利用: ${extra.get('spend', 0)} / ${extra['limit']}")
        if not st.windows:
            st.error = "利用量データなし"
            log.warning("claude usage unexpected body: %s", str(body)[:500])
        st.updated = datetime.now()
        return st

    def _usage(self, cred):
        return http_json(
            "https://api.anthropic.com/api/oauth/usage",
            headers={
                "Authorization": "Bearer " + cred["accessToken"],
                "anthropic-beta": "oauth-2025-04-20",
            },
        )

    def _refresh(self, data, cred, st):
        status, body = http_json(
            "https://console.anthropic.com/v1/oauth/token",
            payload={
                "grant_type": "refresh_token",
                "refresh_token": cred.get("refreshToken", ""),
                "client_id": CLAUDE_CLIENT_ID,
            },
            method="POST",
        )
        if status != 200 or not isinstance(body, dict):
            st.error = "要ログイン (claude /login)"
            log.warning("claude refresh %s: %s", status, str(body)[:300])
            return False
        cred["accessToken"] = body["access_token"]
        if body.get("refresh_token"):
            cred["refreshToken"] = body["refresh_token"]
        cred["expiresAt"] = int((time.time() + body.get("expires_in", 28800)) * 1000)
        if body.get("scope"):
            cred["scopes"] = body["scope"].split()
        try:
            atomic_write_json(CLAUDE_CRED_PATH, data)
        except Exception as e:
            log.error("claude cred write-back failed: %r", e)
        log.info("claude token refreshed")
        return True


# ---------------------------------------------------------------- Codex

class CodexProvider:
    name = "Codex"

    def fetch(self):
        st = ProviderState(self.name)
        try:
            with open(CODEX_AUTH_PATH, encoding="utf-8") as f:
                auth = json.load(f)
            tokens = auth["tokens"]
        except Exception as e:
            st.error = "認証ファイルなし (codex login)"
            log.warning("codex auth: %r", e)
            return st

        status, body = self._usage(tokens)
        if status == 401:
            if not self._refresh(auth, tokens, st):
                return st
            status, body = self._usage(tokens)

        if status != 200 or not isinstance(body, dict):
            st.error = f"取得失敗 ({status})"
            log.warning("codex usage %s: %s", status, str(body)[:300])
            return st

        st.plan = str(body.get("plan_type") or "")
        rl = body.get("rate_limit") or {}
        for key in ("primary_window", "secondary_window"):
            w = rl.get(key)
            if isinstance(w, dict):
                secs = w.get("limit_window_seconds") or 0
                label = "5時間" if secs <= 6 * 3600 else "週"
                st.windows.append(Window(label, float(w.get("used_percent", 0)),
                                         parse_reset_dt(w.get("reset_at"))))
        for extra in body.get("additional_rate_limits") or []:
            if isinstance(extra, dict):
                w = extra.get("rate_limit") or extra
                if isinstance(w, dict) and "used_percent" in w:
                    st.windows.append(Window(str(extra.get("id", "追加")),
                                             float(w["used_percent"]),
                                             parse_reset_dt(w.get("reset_at"))))

        # --- 追加情報 (コードレビュー枠 / クレジット / リセットクレジット) ---
        crr = body.get("code_review_rate_limit")
        if isinstance(crr, dict):
            w = crr.get("primary_window") or crr
            if isinstance(w, dict) and "used_percent" in w:
                st.extras.append(f"コードレビュー: {w['used_percent']:.0f}% 使用")
        credits = body.get("credits")
        if isinstance(credits, dict):
            if credits.get("unlimited"):
                st.extras.append("クレジット: 無制限")
            elif credits.get("has_credits"):
                st.extras.append(f"クレジット残高: {credits.get('balance', '0')}")
        rrc = body.get("rate_limit_reset_credits")
        if isinstance(rrc, dict) and rrc.get("available_count"):
            st.extras.append(f"リセットクレジット: {rrc['available_count']}回分")

        if not st.windows:
            st.error = "利用量データなし"
            log.warning("codex usage unexpected body: %s", str(body)[:500])
        st.updated = datetime.now()
        return st

    def _usage(self, tokens):
        headers = {"Authorization": "Bearer " + tokens["access_token"]}
        if tokens.get("account_id"):
            headers["chatgpt-account-id"] = tokens["account_id"]
        return http_json("https://chatgpt.com/backend-api/wham/usage", headers=headers)

    def _refresh(self, auth, tokens, st):
        status, body = http_json(
            "https://auth.openai.com/oauth/token",
            payload={
                "client_id": CODEX_CLIENT_ID,
                "grant_type": "refresh_token",
                "refresh_token": tokens.get("refresh_token", ""),
                "scope": "openid profile email",
            },
            method="POST",
        )
        if status != 200 or not isinstance(body, dict):
            st.error = "要ログイン (codex login)"
            log.warning("codex refresh %s: %s", status, str(body)[:300])
            return False
        tokens["access_token"] = body["access_token"]
        if body.get("refresh_token"):
            tokens["refresh_token"] = body["refresh_token"]
        if body.get("id_token"):
            tokens["id_token"] = body["id_token"]
        auth["last_refresh"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        try:
            atomic_write_json(CODEX_AUTH_PATH, auth)
        except Exception as e:
            log.error("codex auth write-back failed: %r", e)
        log.info("codex token refreshed")
        return True


PROVIDERS = [ClaudeProvider, CodexProvider]
