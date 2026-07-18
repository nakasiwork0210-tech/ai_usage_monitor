# Usage Monitor (Windows)

Claude Code / Codex (ChatGPT) の利用量をタスクトレイに常駐表示する Windows 用アプリ。
macOS の [CodexBar](https://github.com/steipete/CodexBar) と同じ仕組みで、ローカルの CLI 認証情報を使って公式エンドポイントから利用量を取得します。

## 機能

- **トレイアイコン** — 使用率バー(緑 <70% / 黄 <90% / 赤 ≥90%、エラー時 ✕)。表示モードを切り替え可能:
  - 両方(バー2本: 左=Claude、右=Codex)/ Claude のみ / Codex のみ / 自動(使用率最高のプロバイダ)
  - 単独表示時は「%数字で表示」も選択可
- **右クリックメニュー** — 各ウィンドウ(5時間 / 週 / 週 Opus など)の使用率・リセット時刻・**リセットまでのカウントダウン**、Codex の追加情報(コードレビュー枠・クレジット残高・リセットクレジット)
- **ダッシュボード**(左クリック or メニュー) — 利用量メーター + ローカルコストスキャンの日次チャート(**Today / 7d / 30d** 切り替え)
  - Claude: `~/.claude/projects` のセッションログから API 料金換算コストを集計
  - Codex: `~/.codex/sessions` の token_count イベントからトークン数 + gpt-5 換算の参考コスト
- **CLI** — スクリプトや CI から利用量を取得可能
- **ダーク / ライトテーマ** — 自動(Windows の外観設定に追従)/ ライト / ダークを切り替え。ダッシュボードはタイトルバーまで配色が変わり、トレイアイコンの枠線はタスクバーの明暗に自動調整
- 5分ごと自動更新、使用率 90% 超えで Windows 通知
- トークン期限切れは自動リフレッシュ + 元ファイルへ書き戻し(CLI との食い違い防止)

## 仕組み

| プロバイダ | 認証情報 | エンドポイント |
|---|---|---|
| Claude | `~/.claude/.credentials.json` | `GET https://api.anthropic.com/api/oauth/usage` |
| Codex | `~/.codex/auth.json` | `GET https://chatgpt.com/backend-api/wham/usage` |

認証エラー時はトレイに ⚠ を表示します。`claude /login` / `codex login` で再ログインしてください。

## セキュリティ

- **アプリ独自のログイン不要** — Claude Code / Codex CLI が保存済みの認証情報を読むだけ
- **パスワード保存なし** — トークンを独自の場所へコピーしない。リフレッシュ時も各 CLI の元ファイル(`~/.claude/.credentials.json` / `~/.codex/auth.json`)にのみ書き戻す
- **クラウド同期・テレメトリなし** — 外部への送信は一切なし
- **通信は公式 API のみ** — 利用量取得のための OpenAI / Anthropic 公式エンドポイントへの HTTPS のみ(CodexBar と同じ方式)。ローカルコスト集計は完全オンデバイスで、ネットワークを使わない

## インストール (brew cask 相当)

Python 不要の単体 exe をインストール:

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1              # インストール + 起動
powershell -ExecutionPolicy Bypass -File install.ps1 -AutoStart   # 自動起動も ON
powershell -ExecutionPolicy Bypass -File install.ps1 -Uninstall   # アンインストール
```

`%LOCALAPPDATA%\Programs\UsageMonitor` に配置され、スタートメニューに「Usage Monitor」が登録されます。

exe を再ビルドする場合:

```powershell
pip install pyinstaller
pyinstaller --onefile --windowed --name UsageMonitor usage_monitor.py
```

## 開発モードでの起動 (Python から直接)

```powershell
pip install -r requirements.txt
pythonw usage_monitor.py     # トレイ常駐
```

トレイメニューの「Windows 起動時に自動開始」を ON にすると、スタートアップフォルダに起動用 .vbs が作られます。

## CLI

```powershell
python usage_monitor.py --cli      # テキスト表示
python usage_monitor.py --json     # JSON 表示 (スクリプト向け)
python usage_monitor.py --cost 30  # ローカルコスト集計 (直近30日)
```

## 設定 (config.json)

```json
{
  "refresh_minutes": 5,
  "notify_threshold": 90,
  "icon_mode": "both",
  "icon_percent": false,
  "theme": "auto"
}
```

`theme` は `auto`(Windows 設定に追従)/ `light` / `dark`。トレイメニューの「テーマ」やダッシュボード右上のボタンからも切り替えられます。

## ファイル構成

- `usage_monitor.py` — トレイ常駐アプリ + CLI
- `common.py` — 設定 IO とテーマ定義(トレイ・ダッシュボード共通)
- `providers.py` — Claude / Codex API プロバイダ(トークンリフレッシュ含む)
- `localcost.py` — ローカルセッションログの増分コストスキャン
- `dashboard.py` — ダッシュボードウィンドウ(tkinter、テーマ対応)
- `usage_monitor.log` — ログ / `cost_cache.json` — スキャンキャッシュ

## メモ

- コストは公開 API 料金からの**推定値**です(サブスクリプション利用分は実際には課金されません)。Codex のコストは gpt-5 の API 料金換算の参考値です。
- macOS 版 CodexBar の WidgetKit ウィジェットに相当する機能は Windows には無いため、CLI + ダッシュボードで代替しています。OpenAI / Anthropic の Admin API キーによる組織支出チャートは未実装です(必要なら API キーを config に追加する形で拡張可能)。
