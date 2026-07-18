# -*- coding: utf-8 -*-
"""ローカルセッションログのコストスキャン。

Claude: ~/.claude/projects/**/*.jsonl の assistant メッセージの usage からトークン数と
        コスト(API 料金換算)を日次集計する。
Codex : ~/.codex/sessions/YYYY/MM/DD/*.jsonl の token_count イベントからトークン数を
        日次集計し、gpt-5 の API 料金で参考コストを出す。

ファイルは追記型なので、(サイズ, 解析済みオフセット) をキャッシュして増分だけ読む。
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

HOME = os.path.expanduser("~")
APP_DIR = os.path.dirname(sys.executable if getattr(sys, "frozen", False)
                          else os.path.abspath(__file__))
CACHE_PATH = os.path.join(APP_DIR, "cost_cache.json")

CLAUDE_PROJECTS = os.path.join(HOME, ".claude", "projects")
CODEX_SESSIONS = os.path.join(os.environ.get("CODEX_HOME", os.path.join(HOME, ".codex")), "sessions")

# USD / 1M トークン: (入力, 出力, キャッシュ書込, キャッシュ読取)
CLAUDE_PRICING = {
    "fable": (10.0, 50.0, 12.5, 1.0),
    "mythos": (10.0, 50.0, 12.5, 1.0),
    "opus": (5.0, 25.0, 6.25, 0.5),
    "sonnet": (3.0, 15.0, 3.75, 0.3),
    "haiku": (1.0, 5.0, 1.25, 0.1),
}
GPT5_PRICING = (1.25, 10.0, 0.0, 0.125)  # 入力, 出力, -, キャッシュ入力


def _claude_price(model):
    m = (model or "").lower()
    for key, p in CLAUDE_PRICING.items():
        if key in m:
            return p
    return CLAUDE_PRICING["sonnet"]


def _load_cache():
    try:
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(cache):
    try:
        tmp = CACHE_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cache, f)
        os.replace(tmp, CACHE_PATH)
    except Exception:
        pass


def _merge_days(total, days):
    for day, vals in days.items():
        cur = total.setdefault(day, {"cost": 0.0, "input": 0, "output": 0, "cache_read": 0})
        for k in cur:
            cur[k] += vals.get(k, 0)


def _parse_claude_file(path, offset, days):
    """offset 以降を解析して days に加算。新しいオフセットを返す。"""
    with open(path, "rb") as f:
        f.seek(offset)
        for raw in f:
            offset += len(raw)
            if b'"usage"' not in raw:
                continue
            try:
                rec = json.loads(raw.decode("utf-8", errors="replace"))
                if rec.get("type") != "assistant":
                    continue
                msg = rec.get("message") or {}
                usage = msg.get("usage")
                if not isinstance(usage, dict):
                    continue
                ts = rec.get("timestamp", "")
                day = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d")
                inp = usage.get("input_tokens", 0) or 0
                out = usage.get("output_tokens", 0) or 0
                cw = usage.get("cache_creation_input_tokens", 0) or 0
                cr = usage.get("cache_read_input_tokens", 0) or 0
                p_in, p_out, p_cw, p_cr = _claude_price(msg.get("model"))
                cost = (inp * p_in + out * p_out + cw * p_cw + cr * p_cr) / 1_000_000
                d = days.setdefault(day, {"cost": 0.0, "input": 0, "output": 0, "cache_read": 0})
                d["cost"] += cost
                d["input"] += inp + cw
                d["output"] += out
                d["cache_read"] += cr
            except Exception:
                continue
    return offset


def _parse_codex_file(path, offset, days):
    with open(path, "rb") as f:
        f.seek(offset)
        for raw in f:
            offset += len(raw)
            if b'"token_count"' not in raw:
                continue
            try:
                rec = json.loads(raw.decode("utf-8", errors="replace"))
                info = ((rec.get("payload") or {}).get("info")) or {}
                last = info.get("last_token_usage")
                if not isinstance(last, dict):
                    continue
                ts = rec.get("timestamp", "")
                day = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d")
                inp = last.get("input_tokens", 0) or 0
                cached = last.get("cached_input_tokens", 0) or 0
                out = last.get("output_tokens", 0) or 0
                p_in, p_out, _, p_cache = GPT5_PRICING
                cost = ((inp - cached) * p_in + cached * p_cache + out * p_out) / 1_000_000
                d = days.setdefault(day, {"cost": 0.0, "input": 0, "output": 0, "cache_read": 0})
                d["cost"] += max(cost, 0.0)
                d["input"] += inp
                d["output"] += out
                d["cache_read"] += cached
            except Exception:
                continue
    return offset


def _scan(root, pattern_days, parser, cache_key, cache, cutoff):
    """root 以下の .jsonl を増分スキャンして日次集計を返す。"""
    total = {}
    fcache = cache.setdefault(cache_key, {})
    seen_paths = set()
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            if not fn.endswith(".jsonl"):
                continue
            path = os.path.join(dirpath, fn)
            try:
                stat = os.stat(path)
            except OSError:
                continue
            if datetime.fromtimestamp(stat.st_mtime) < cutoff:
                continue  # 集計期間より古い(日次データはキャッシュに残っていれば拾う)
            seen_paths.add(path)
            ent = fcache.get(path)
            if ent and ent.get("size") == stat.st_size:
                _merge_days(total, ent.get("days", {}))
                continue
            days = dict(ent.get("days", {})) if ent and stat.st_size > ent.get("offset", 0) else {}
            offset = ent.get("offset", 0) if days else 0
            try:
                offset = parser(path, offset, days)
            except OSError:
                continue
            fcache[path] = {"size": stat.st_size, "offset": offset, "days": days}
            _merge_days(total, days)
    # 期間内だが今回歩かなかったキャッシュ済みファイル(古い mtime)も合算
    for path, ent in fcache.items():
        if path not in seen_paths and any(d >= cutoff.strftime("%Y-%m-%d") for d in ent.get("days", {})):
            _merge_days(total, ent["days"])
    return total


def scan(days=30):
    """{'claude': {day: {...}}, 'codex': {day: {...}}} を返す。day は YYYY-MM-DD。"""
    cutoff = datetime.now() - timedelta(days=days + 1)
    cache = _load_cache()
    result = {"claude": {}, "codex": {}}
    if os.path.isdir(CLAUDE_PROJECTS):
        result["claude"] = _scan(CLAUDE_PROJECTS, days, _parse_claude_file, "claude", cache, cutoff)
    if os.path.isdir(CODEX_SESSIONS):
        result["codex"] = _scan(CODEX_SESSIONS, days, _parse_codex_file, "codex", cache, cutoff)
    _save_cache(cache)
    # 期間でフィルタ
    lo = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    for key in result:
        result[key] = {d: v for d, v in sorted(result[key].items()) if d >= lo}
    return result


def series(daily, days):
    """日次 dict → 直近 days 日ぶんの (日付ラベル, コスト, トークン) の連続リスト。"""
    out = []
    today = datetime.now().date()
    for i in range(days - 1, -1, -1):
        day = today - timedelta(days=i)
        key = day.strftime("%Y-%m-%d")
        v = daily.get(key, {})
        out.append((day.strftime("%m/%d"), v.get("cost", 0.0),
                    v.get("input", 0) + v.get("output", 0)))
    return out
