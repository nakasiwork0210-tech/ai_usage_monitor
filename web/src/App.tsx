import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Download,
  Github,
  Gauge,
  Timer,
  BarChart3,
  MoonStar,
  Bell,
  ShieldCheck,
  Sun,
  Moon,
  Cpu,
  Lock,
  CloudOff,
  Wifi,
  Terminal,
} from "lucide-react";

const REPO = "https://github.com/nakasiwork0210-tech/ai_usage_monitor";
const DOWNLOAD = `${REPO}/releases/latest/download/UsageMonitor.exe`;
const RELEASES = `${REPO}/releases`;

/* ---------------------------------------------------------------- テーマ */
function useTheme() {
  const [dark, setDark] = useState(() =>
    document.documentElement.classList.contains("dark"),
  );
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem("theme", dark ? "dark" : "light");
  }, [dark]);
  return { dark, toggle: () => setDark((d) => !d) };
}

/* ---------------------------------------------------------------- 部品 */
const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0 },
};

function Logo({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" className={className} aria-hidden>
      <rect x="6" y="2" width="22" height="60" rx="6" fill="none" stroke="currentColor" strokeWidth="3" opacity="0.4" />
      <rect x="9" y="30" width="16" height="29" rx="3" className="fill-good" />
      <rect x="36" y="2" width="22" height="60" rx="6" fill="none" stroke="currentColor" strokeWidth="3" opacity="0.4" />
      <rect x="39" y="14" width="16" height="45" rx="3" className="fill-peach" />
    </svg>
  );
}

function Bar({ pct, color, delay = 0 }: { pct: number; color: string; delay?: number }) {
  return (
    <div className="h-4 flex-1 overflow-hidden rounded-full bg-neutral-200 dark:bg-neutral-700/60">
      <motion.div
        className={`h-full rounded-full ${color}`}
        initial={{ width: 0 }}
        whileInView={{ width: `${pct}%` }}
        viewport={{ once: true }}
        transition={{ duration: 1, delay, ease: "easeOut" }}
      />
    </div>
  );
}

function MeterRow({ name, pct, color, delay }: { name: string; pct: number; color: string; delay: number }) {
  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="w-28 text-neutral-500 dark:text-neutral-400">{name}</span>
      <Bar pct={pct} color={color} delay={delay} />
      <span className="w-12 text-right tabular-nums font-medium">{pct}%</span>
    </div>
  );
}

function MockDashboard() {
  return (
    <div className="rounded-2xl border border-neutral-200 bg-white/80 p-6 shadow-2xl shadow-brand/10 backdrop-blur dark:border-neutral-700 dark:bg-[#1e1e2e]/80">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-sm font-semibold text-brand">Claude <span className="font-normal text-neutral-400">(Pro)</span></span>
        <span className="text-xs text-neutral-400">更新: 22:41</span>
      </div>
      <div className="space-y-2">
        <MeterRow name="5時間" pct={45} color="bg-good" delay={0.1} />
        <MeterRow name="週" pct={26} color="bg-good" delay={0.2} />
      </div>
      <div className="my-4 h-px bg-neutral-200 dark:bg-neutral-700" />
      <div className="mb-3 text-sm font-semibold text-peach">Codex <span className="font-normal text-neutral-400">(Plus)</span></div>
      <div className="space-y-2">
        <MeterRow name="週" pct={78} color="bg-warn" delay={0.3} />
        <MeterRow name="コードレビュー" pct={12} color="bg-good" delay={0.4} />
      </div>
    </div>
  );
}

function Cmd({ children }: { children: React.ReactNode }) {
  return (
    <div className="mt-2 flex items-center gap-2 rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 font-mono text-xs text-neutral-700 dark:border-neutral-700 dark:bg-black/40 dark:text-neutral-200">
      <span className="select-none text-brand">$</span>
      <code className="overflow-x-auto whitespace-nowrap">{children}</code>
    </div>
  );
}

function Section({ id, children, className = "" }: { id?: string; children: React.ReactNode; className?: string }) {
  return (
    <section id={id} className={`mx-auto max-w-5xl px-5 py-20 ${className}`}>
      {children}
    </section>
  );
}

function Reveal({ children, delay = 0 }: { children: React.ReactNode; delay?: number }) {
  return (
    <motion.div
      variants={fadeUp}
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.5, delay }}
    >
      {children}
    </motion.div>
  );
}

/* ---------------------------------------------------------------- データ */
const FEATURES = [
  { icon: Gauge, title: "トレイに使用率", desc: "Claude / Codex の使用率をバーで常時表示。緑・黄・赤で残量がひと目でわかる。" },
  { icon: Timer, title: "リセットまで表示", desc: "5時間・週の各枠がいつリセットされるか、残り時間をカウントダウン。" },
  { icon: BarChart3, title: "コストダッシュボード", desc: "ローカルログから日次コストを集計。Today / 7日 / 30日で切り替え。" },
  { icon: MoonStar, title: "ダーク / ライト", desc: "Windows の外観設定に自動追従。手動固定も可能。" },
  { icon: Bell, title: "使いすぎ通知", desc: "使用率が 90% を超えると Windows 通知でお知らせ。" },
  { icon: ShieldCheck, title: "安全設計", desc: "独自ログインなし・パスワード保存なし・クラウド同期なし。" },
];

const SECURITY = [
  { icon: Cpu, title: "ローカルデータのみ", desc: "CLI が保存済みの認証情報を読むだけ。独自のログイン画面はありません。" },
  { icon: Lock, title: "パスワード保存なし", desc: "トークンを別の場所へコピーしません。更新時も元ファイルに書き戻すだけ。" },
  { icon: CloudOff, title: "クラウド同期なし", desc: "テレメトリや外部サーバーへの送信は一切ありません。" },
  { icon: Wifi, title: "公式 API のみ", desc: "通信は利用量取得のための公式エンドポイントへの HTTPS のみ。集計はオフライン。" },
];

/* ---------------------------------------------------------------- App */
export default function App() {
  const { dark, toggle } = useTheme();

  return (
    <div className="relative overflow-x-hidden">
      {/* ナビ */}
      <header className="sticky top-0 z-50 border-b border-neutral-200/60 bg-neutral-50/70 backdrop-blur-md dark:border-neutral-800/60 dark:bg-[#11111b]/70">
        <nav className="mx-auto flex max-w-5xl items-center justify-between px-5 py-3">
          <a href="#top" className="flex items-center gap-2 font-semibold">
            <Logo className="h-6 w-6" />
            Usage Monitor
          </a>
          <div className="flex items-center gap-1 text-sm sm:gap-4">
            <a href="#features" className="hidden px-2 text-neutral-500 hover:text-brand sm:inline dark:text-neutral-400">機能</a>
            <a href="#login" className="hidden px-2 text-neutral-500 hover:text-brand sm:inline dark:text-neutral-400">ログイン</a>
            <a href="#security" className="hidden px-2 text-neutral-500 hover:text-brand sm:inline dark:text-neutral-400">セキュリティ</a>
            <a href={REPO} className="hidden items-center gap-1 px-2 text-neutral-500 hover:text-brand sm:flex dark:text-neutral-400">
              <Github className="h-4 w-4" /> GitHub
            </a>
            <button
              onClick={toggle}
              aria-label="テーマ切り替え"
              className="rounded-lg p-2 text-neutral-500 transition hover:bg-neutral-200 dark:text-neutral-400 dark:hover:bg-neutral-800"
            >
              {dark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            </button>
          </div>
        </nav>
      </header>

      {/* ヒーロー */}
      <div id="top" className="glow relative">
        <Section className="!pt-20 text-center">
          <motion.div initial="hidden" animate="show" variants={fadeUp} transition={{ duration: 0.5 }}>
            <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-neutral-200 bg-white/60 px-4 py-1.5 text-xs text-neutral-500 dark:border-neutral-700 dark:bg-neutral-800/50 dark:text-neutral-400">
              <span className="h-2 w-2 rounded-full bg-good" /> Windows 常駐 · Claude &amp; Codex 対応 · オープンソース
            </div>
            <h1 className="mx-auto max-w-3xl bg-gradient-to-br from-brand to-brand-2 bg-clip-text text-4xl font-bold leading-tight tracking-tight text-transparent sm:text-6xl">
              Claude / Codex の利用量を<br />タスクトレイで見張る
            </h1>
            <p className="mx-auto mt-6 max-w-xl text-lg text-neutral-500 dark:text-neutral-400">
              Claude Code と Codex (ChatGPT) の残量・リセット時刻・コストを Windows の常駐アプリで。
              ログイン不要・完全オンデバイス。
            </p>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
              <a
                href={DOWNLOAD}
                className="group inline-flex items-center gap-2 rounded-xl bg-brand px-7 py-3.5 font-semibold text-white shadow-lg shadow-brand/30 transition hover:-translate-y-0.5 hover:shadow-xl hover:shadow-brand/40"
              >
                <Download className="h-5 w-5 transition group-hover:translate-y-0.5" />
                Windows 版をダウンロード
                <span className="text-xs font-normal opacity-80">.exe</span>
              </a>
              <a
                href={REPO}
                className="inline-flex items-center gap-2 rounded-xl border border-neutral-300 px-6 py-3.5 font-medium transition hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-800"
              >
                <Github className="h-5 w-5" /> ソースコード
              </a>
            </div>
            <p className="mt-4 text-sm text-neutral-400">
              無料・オープンソース (MIT) ・ Python 不要 ・ Windows 10 / 11 ・ 約 25 MB
            </p>
          </motion.div>

          <motion.div
            className="mx-auto mt-14 max-w-md"
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            <MockDashboard />
          </motion.div>
        </Section>
      </div>

      {/* 機能 */}
      <Section id="features">
        <Reveal>
          <h2 className="mb-2 text-center text-3xl font-bold">できること</h2>
          <p className="mb-12 text-center text-neutral-500 dark:text-neutral-400">
            残量の把握からコスト分析まで、これひとつで。
          </p>
        </Reveal>
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f, i) => (
            <Reveal key={f.title} delay={i * 0.05}>
              <div className="group h-full rounded-2xl border border-neutral-200 bg-white p-6 transition hover:-translate-y-1 hover:border-brand/50 hover:shadow-lg hover:shadow-brand/5 dark:border-neutral-800 dark:bg-neutral-900/50">
                <div className="mb-4 inline-flex rounded-xl bg-brand/10 p-3 text-brand transition group-hover:scale-110">
                  <f.icon className="h-6 w-6" />
                </div>
                <h3 className="mb-1.5 font-semibold">{f.title}</h3>
                <p className="text-sm text-neutral-500 dark:text-neutral-400">{f.desc}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </Section>

      {/* 使い方 */}
      <div className="bg-neutral-100/60 dark:bg-neutral-900/30">
        <Section>
          <Reveal>
            <h2 className="mb-12 text-center text-3xl font-bold">3ステップで開始</h2>
          </Reveal>
          <div className="grid gap-6 md:grid-cols-3">
            {[
              { n: "1", t: "ダウンロード", d: "UsageMonitor.exe を落として実行するだけ。Python も他のランタイムも不要。" },
              { n: "2", t: "トレイに常駐", d: "左クリックでダッシュボード、右クリックでメニュー。設定は自動保存。" },
              { n: "3", t: "そのまま表示", d: "Claude / Codex CLI にログイン済みなら、追加設定なしで利用量が出ます。" },
            ].map((s, i) => (
              <Reveal key={s.n} delay={i * 0.08}>
                <div className="h-full rounded-2xl border border-neutral-200 bg-white p-6 dark:border-neutral-800 dark:bg-neutral-900/50">
                  <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-brand to-brand-2 font-bold text-white">
                    {s.n}
                  </div>
                  <h3 className="mb-1.5 font-semibold">{s.t}</h3>
                  <p className="text-sm text-neutral-500 dark:text-neutral-400">{s.d}</p>
                </div>
              </Reveal>
            ))}
          </div>
          <Reveal delay={0.2}>
            <div className="mx-auto mt-8 max-w-2xl rounded-xl border border-warn/30 bg-warn/5 px-5 py-4 text-sm text-neutral-600 dark:text-neutral-300">
              💡 署名なしの exe のため、初回起動時に Windows SmartScreen が警告することがあります。
              その場合は <b>[詳細情報] → [実行]</b> で起動できます。中身が気になる場合は
              <a href={`${REPO}#開発モードでの起動-python-から直接`} className="text-brand hover:underline"> ソースからビルド</a> も可能です。
            </div>
          </Reveal>
        </Section>
      </div>

      {/* ログイン方法 */}
      <Section id="login">
        <Reveal>
          <h2 className="mb-2 text-center text-3xl font-bold">
            <Terminal className="mr-2 inline h-7 w-7 text-brand" />
            CLI にログインしておく
          </h2>
          <p className="mb-12 text-center text-neutral-500 dark:text-neutral-400">
            アプリは各 CLI が保存した認証情報を読むだけ。どちらか一方だけでも動きます。
          </p>
        </Reveal>
        <div className="grid gap-5 md:grid-cols-2">
          <Reveal>
            <div className="h-full rounded-2xl border border-neutral-200 bg-white p-6 dark:border-neutral-800 dark:bg-neutral-900/50">
              <h3 className="mb-1 flex items-center gap-2 font-semibold text-brand">Claude Code CLI</h3>
              <p className="mb-4 text-sm text-neutral-500 dark:text-neutral-400">未導入なら Node.js を入れてインストール:</p>
              <Cmd>npm install -g @anthropic-ai/claude-code</Cmd>
              <p className="mb-1 mt-4 text-sm text-neutral-500 dark:text-neutral-400">起動してログイン:</p>
              <Cmd>claude</Cmd>
              <ol className="mt-4 space-y-1.5 pl-5 text-sm text-neutral-600 dark:text-neutral-300" style={{ listStyleType: "decimal" }}>
                <li>プロンプトで <code className="rounded bg-neutral-200 px-1.5 py-0.5 text-xs dark:bg-neutral-700">/login</code> を実行(未ログインなら自動で表示)</li>
                <li><b>Claude account with subscription</b>(Pro / Max)を選択</li>
                <li>ブラウザで承認。開かない場合は表示 URL とワンタイムコードで認証</li>
              </ol>
            </div>
          </Reveal>
          <Reveal delay={0.08}>
            <div className="h-full rounded-2xl border border-neutral-200 bg-white p-6 dark:border-neutral-800 dark:bg-neutral-900/50">
              <h3 className="mb-1 flex items-center gap-2 font-semibold text-peach">Codex CLI</h3>
              <p className="mb-4 text-sm text-neutral-500 dark:text-neutral-400">未導入ならインストール:</p>
              <Cmd>npm install -g @openai/codex</Cmd>
              <p className="mb-1 mt-4 text-sm text-neutral-500 dark:text-neutral-400">ログイン:</p>
              <Cmd>codex login</Cmd>
              <ol className="mt-4 space-y-1.5 pl-5 text-sm text-neutral-600 dark:text-neutral-300" style={{ listStyleType: "decimal" }}>
                <li>ブラウザが開く</li>
                <li>ChatGPT アカウント(Plus / Pro)でサインイン</li>
                <li>完了すると <code className="rounded bg-neutral-200 px-1.5 py-0.5 text-xs dark:bg-neutral-700">~/.codex/auth.json</code> に保存</li>
              </ol>
            </div>
          </Reveal>
        </div>
        <Reveal delay={0.15}>
          <p className="mx-auto mt-8 max-w-2xl text-center text-sm text-neutral-500 dark:text-neutral-400">
            ログイン後、Usage Monitor は次の自動更新(最大5分)で反映します。すぐ見たい場合はトレイメニューの「今すぐ更新」を。
          </p>
        </Reveal>
      </Section>

      {/* セキュリティ */}
      <Section id="security">
        <Reveal>
          <h2 className="mb-2 text-center text-3xl font-bold">
            <ShieldCheck className="mr-2 inline h-7 w-7 text-good" />
            プライバシー・ファースト
          </h2>
          <p className="mb-12 text-center text-neutral-500 dark:text-neutral-400">
            あなたのデータは、あなたの PC から出ません。
          </p>
        </Reveal>
        <div className="grid gap-5 sm:grid-cols-2">
          {SECURITY.map((s, i) => (
            <Reveal key={s.title} delay={i * 0.05}>
              <div className="flex h-full gap-4 rounded-2xl border border-neutral-200 bg-white p-6 dark:border-neutral-800 dark:bg-neutral-900/50">
                <div className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-good/10 text-good">
                  <s.icon className="h-6 w-6" />
                </div>
                <div>
                  <h3 className="mb-1 font-semibold">{s.title}</h3>
                  <p className="text-sm text-neutral-500 dark:text-neutral-400">{s.desc}</p>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </Section>

      {/* CTA */}
      <Section className="text-center">
        <Reveal>
          <div className="glow rounded-3xl border border-neutral-200 bg-white/50 px-6 py-16 dark:border-neutral-800 dark:bg-neutral-900/40">
            <h2 className="text-3xl font-bold sm:text-4xl">今すぐ使ってみる</h2>
            <p className="mx-auto mt-3 max-w-md text-neutral-500 dark:text-neutral-400">
              ダウンロードして実行するだけ。数秒でトレイに常駐します。
            </p>
            <a
              href={DOWNLOAD}
              className="mt-8 inline-flex items-center gap-2 rounded-xl bg-brand px-8 py-4 text-lg font-semibold text-white shadow-lg shadow-brand/30 transition hover:-translate-y-0.5 hover:shadow-xl hover:shadow-brand/40"
            >
              <Download className="h-5 w-5" /> UsageMonitor.exe をダウンロード
            </a>
          </div>
        </Reveal>
      </Section>

      {/* フッター */}
      <footer className="border-t border-neutral-200 py-10 text-center text-sm text-neutral-500 dark:border-neutral-800 dark:text-neutral-400">
        <div className="flex justify-center gap-4">
          <a href={REPO} className="hover:text-brand">GitHub</a>
          <a href={RELEASES} className="hover:text-brand">リリース</a>
          <a href={`${REPO}/blob/main/LICENSE`} className="hover:text-brand">MIT License</a>
        </div>
        <p className="mt-3">
          Anthropic / OpenAI とは無関係の非公式・個人開発ツールです。
        </p>
      </footer>
    </div>
  );
}
