# v1.0.0 — Usage Monitor for Windows

Claude Code / Codex (ChatGPT) の利用量を Windows タスクトレイに常駐表示するアプリの初回リリース。

## 使い方

1. 下の `UsageMonitor.exe` をダウンロードして実行(Python 不要)
2. タスクトレイに常駐します。左クリックでダッシュボード、右クリックでメニュー
3. Claude / Codex の各 CLI でログイン済みなら、そのまま利用量が表示されます

> 署名なし exe のため SmartScreen が警告する場合があります。**[詳細情報] → [実行]** で起動してください。

## 主な機能

- トレイアイコンに使用率バー(緑/黄/赤)。両方 / Claude のみ / Codex のみ / 自動 の表示切替
- リセットまでのカウントダウン、Codex のコードレビュー枠・クレジット残高表示
- ダッシュボード: 利用量メーター + ローカルコストの日次チャート(Today / 7d / 30d)
- ダーク / ライト / 自動テーマ
- 5分ごと自動更新、90% 超えで通知、トークン自動リフレッシュ
- CLI: `UsageMonitor.exe --cli` / `--json` / `--cost 30`

## セキュリティ

ローカルの CLI 認証情報を読むだけで、独自ログイン・パスワード保存・クラウド同期はありません。通信は利用量取得のための OpenAI / Anthropic 公式 API のみです。

詳細は [README](https://github.com/nakasiwork0210-tech/ai_usage_monitor#readme) を参照。
