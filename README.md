<p align="center">
  <img src="assets/banner.png" alt="Hermes Agent" width="100%">
</p>

# Dexall ALL AI5.2 TACT
<p align="center">
  <a href="https://hermes-agent.nousresearch.com/">Hermes Agent</a> | <a href="https://hermes-agent.nousresearch.com/">Hermes Desktop</a>
</p>
<p align="center">
  <a href="https://hermes-agent.nousresearch.com/docs/"><img src="https://img.shields.io/badge/Docs-hermes--agent.nousresearch.com-FFD700?style=for-the-badge" alt="Documentation"></a>
  <a href="https://discord.gg/NousResearch"><img src="https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Discord"></a>
  <a href="https://github.com/NousResearch/hermes-agent/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <a href="https://nousresearch.com"><img src="https://img.shields.io/badge/Built%20by-Nous%20Research-blueviolet?style=for-the-badge" alt="Built by Nous Research"></a>
  <a href="README.zh-CN.md"><img src="https://img.shields.io/badge/Lang-中文-red?style=for-the-badge" alt="中文"></a>
  <a href="README.ur-pk.md"><img src="https://img.shields.io/badge/Lang-اردو-green?style=for-the-badge" alt="اردو"></a>
  <a href="README.es.md"><img src="https://img.shields.io/badge/Lang-Español-orange?style=for-the-badge" alt="Español"></a>
</p>

**[Nous Research](https://nousresearch.com) が開発した自己改善型 AI エージェント。** 学習ループを内蔵した唯一のエージェントです。経験からスキルを生み出し、使用中にスキルを改善し、知識を永続化するよう自ら促し、過去の会話を検索し、セッションをまたいであなたについての理解を深めていきます。$5 の VPS、GPU クラスタ、またはアイドル時にほぼコストがかからないサーバーレス基盤で実行できます。ノート PC に縛られません。クラウド VM で動作させながら、Telegram から話しかけられます。

任意のモデルを使用できます — [Nous Portal](https://portal.nousresearch.com)、OpenRouter、OpenAI、独自エンドポイント、[その他多数](https://hermes-agent.nousresearch.com/docs/integrations/providers)。`hermes model` で切り替え — コード変更もロックインもありません。

<table>
<tr><td><b>本物のターミナルインターフェース</b></td><td>複数行編集、スラッシュコマンドのオートコンプリート、会話履歴、割り込みとリダイレクト、ストリーミング形式のツール出力を備えた本格的な TUI。</td></tr>
<tr><td><b>あなたのいる場所で動作</b></td><td>Telegram、Discord、Slack、WhatsApp、Signal、CLI — すべて単一のゲートウェイプロセスから。音声メモの文字起こし、クロスプラットフォームでの会話継続。</td></tr>
<tr><td><b>閉じた学習ループ</b></td><td>エージェントがキュレーションするメモリと定期的なナッジ。複雑なタスク後の自律的なスキル作成。使用中にスキルが自己改善。FTS5 によるセッション検索と LLM 要約でセッションをまたいだ想起を実現。<a href="https://github.com/plastic-labs/honcho">Honcho</a> による弁証法的ユーザーモデリング。<a href="https://agentskills.io">agentskills.io</a> オープン標準と互換。</td></tr>
<tr><td><b>スケジュール自動化</b></td><td>内蔵の cron スケジューラ。任意のプラットフォームへ配信可能。日次レポート、夜間バックアップ、週次監査 — すべて自然言語で、無人で実行。</td></tr>
<tr><td><b>委任と並列化</b></td><td>並列ワークストリーム用に隔離されたサブエージェントを起動。Desktop では Settings → Model → Subagents でプロバイダー、モデル、制限を選択し、完全なルートを Apply。RPC 経由でツールを呼び出す Python スクリプトを書き、多段パイプラインをコンテキストコストゼロのターンに集約。</td></tr>
<tr><td><b>ノート PC だけでなくどこでも実行</b></td><td>6 つの内蔵ターミナルバックエンド — local、Docker、SSH、Modal、Daytona、Vercel Sandbox — に加え、Singularity/Apptainer などのプラグインバックエンド。Daytona と Modal はサーバーレス永続化を提供 — アイドル時はエージェント環境が休止し、要求時に起動、セッション間のコストはほぼゼロ。$5 の VPS や GPU クラスタでも実行可能。</td></tr>
<tr><td><b>研究対応</b></td><td>バッチ軌跡生成、次世代のツール呼び出しモデルを訓練するための軌跡圧縮。</td></tr>
</table>

---

このリポジトリは Dexall が保守する Hermes Agent のフォークです。ソース版の更新先は Dexall の `develop` ブランチです。

## クイックインストール

### Linux、macOS、WSL2

```bash
curl -fsSL https://raw.githubusercontent.com/Dexall-Inc/dexall-ai-agent-desktop/develop/scripts/install.sh | bash
```

### Windows（ネイティブ、PowerShell）

> **注意:** ネイティブ Windows は WSL なしで Hermes を実行します — CLI、ゲートウェイ、TUI、ツールすべてがネイティブに動作します。WSL2 を使いたい場合は、上記の Linux/macOS 用ワンライナーがそちらでも動作します。バグを見つけましたか？ [issue を報告](https://github.com/NousResearch/hermes-agent/issues)してください。

PowerShell で実行:

```powershell
iex (irm https://raw.githubusercontent.com/Dexall-Inc/dexall-ai-agent-desktop/develop/scripts/install.ps1)
```

ソースインストーラは Python 3.14、Node.js、npm、pnpm、ripgrep、FFmpeg、および Python 依存関係の導入を PM に委任します。Git が存在しない場合は、検証済みの Git for Windows アーカイブを Hermes のツールストアにステージングします。システムの Git を置き換えることはありません。別途の MSIX/App Installer パッケージとその更新所有権については、[インストール方法](https://hermes-agent.nousresearch.com/docs/getting-started/installation)を参照してください。

> **Android / Termux:** aarch64 デバイス向けに署名済み APT リポジトリが利用可能です。`stable` チャンネル（タグ付きリリース）とプレリリースの `canary` チャンネルがあります。パッケージには Python、Node.js、TUI が含まれます。デスクトップ/サーバー用インストーラスクリプトではなく、[Termux ガイド](https://hermes-agent.nousresearch.com/docs/getting-started/termux)を使用してください。
>
> **Windows:** ネイティブ Windows は完全にサポートされています — 上記の PowerShell ワンライナーで全てインストールされます。WSL2 を使いたい場合は、Linux 用コマンドがそちらでも動作します。ネイティブ Windows のインストール先は `%LOCALAPPDATA%\hermes`、WSL2 のインストール先は Linux と同様に `~/.hermes` です。

インストール後:

```bash
source ~/.bashrc    # シェルを再読み込み（または: source ~/.zshrc）
hermes              # チャット開始！
```

### トラブルシューティング

#### Windows Defender またはアンチウイルスが `uv.exe` をマルウェアとして検出する場合

アンチウイルス（Bitdefender、Windows Defender など）が Hermes の `bin` フォルダ（`%LOCALAPPDATA%\hermes\bin\uv.exe`）から `uv.exe` を隔離する場合、これは**誤検知**です。このファイルは Astral の `uv` — Hermes が Python 環境を管理するために同梱している Rust 製 Python パッケージマネージャです。ML ベースのアンチウイルスエンジンは、パッケージをダウンロード・インストールする署名なし Rust バイナリを頻繁に検出します。

**コピーが正規のものであることを確認するには:**

```powershell
# 必要に応じて GitHub CLI をインストール
winget install --id GitHub.cli

# GitHub にログイン
gh auth login

# 検証を実行
$uv = "$env:LOCALAPPDATA\hermes\bin\uv.exe"
$ver = (& $uv --version).Split(' ')[1]
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$zip = "$env:TEMP\uv.zip"
Invoke-WebRequest "https://github.com/astral-sh/uv/releases/download/$ver/uv-x86_64-pc-windows-msvc.zip" -OutFile $zip -UseBasicParsing
gh attestation verify $zip --repo astral-sh/uv
Expand-Archive $zip "$env:TEMP\uv_x" -Force
(Get-FileHash "$env:TEMP\uv_x\uv.exe").Hash -eq (Get-FileHash $uv).Hash
```

attestation が "Verification succeeded" と表示され、最後の行が `True` を出力すれば問題ありません。

**Hermes をホワイトリストに登録するには:**
- **Windows Defender:** PowerShell を管理者として実行 → `Add-MpPreference -ExclusionPath "$env:LOCALAPPDATA\hermes\bin"`
- **Bitdefender:** Bitdefender コンソールで例外を追加（Protection > Antivirus > Settings > Manage Exceptions）
- **ファイルハッシュではなくフォルダ**をホワイトリストに登録 — Hermes は `uv` を更新するため、ハッシュはバージョンごとに変わります

詳細は上流の Astral の報告を参照: [astral-sh/uv#13553](https://github.com/astral-sh/uv/issues/13553)、[astral-sh/uv#15011](https://github.com/astral-sh/uv/issues/15011)、[astral-sh/uv#10079](https://github.com/astral-sh/uv/issues/10079)。

---

## はじめに

```bash
hermes              # 対話型 CLI — 会話を開始
hermes model        # LLM プロバイダーとモデルを選択
hermes tools        # 有効にするツールを設定
hermes config set   # 個別の設定値を設定
hermes config get   # 個別の設定値を表示
hermes gateway      # メッセージングゲートウェイを開始（Telegram、Discord など）
hermes setup        # セットアップウィザードを実行（すべてを一度に設定）
hermes update       # 最新バージョンに更新
hermes doctor       # 問題を診断
```

📖 **[完全なドキュメント →](https://hermes-agent.nousresearch.com/docs/)**

---

## API キー収集をスキップ — Nous Portal

Hermes は任意のプロバイダーで動作します — それは変わりません。しかし、モデル、Web 検索、画像生成、TTS、クラウドブラウザ用に 5 つの別々の API キーを集めたくない場合は、**[Nous Portal](https://portal.nousresearch.com)** がそれらすべてを 1 つのサブスクリプションでカバーします:

- **300+ モデル** — `/model <name>` で任意のモデルを選択
- **Tool Gateway** — Web 検索、画像生成（FAL）、テキスト読み上げ（OpenAI）、ブラウザ（Browser Use）をすべてサブスクリプション経由でルーティング。追加アカウント不要。

新規インストールからの 1 コマンド:

```bash
hermes setup --portal
```

これで OAuth 経由でログインし、Nous をプロバイダーに設定し、Tool Gateway を有効にします。配線状況はいつでも `hermes portal info` で確認できます。詳細は [Tool Gateway ドキュメントページ](https://hermes-agent.nousresearch.com/docs/user-guide/features/tool-gateway)を参照してください。

いつでもツールごとに独自のキーを持ち込めます — ゲートウェイはバックエンド単位であり、全か無かではありません。

---

## CLI とメッセージングのクイックリファレンス

Hermes には 2 つのエントリポイントがあります: `hermes` でターミナル UI を開始するか、ゲートウェイを実行して Telegram、Discord、Slack、WhatsApp、Signal、Email から話しかけます。会話に入ると、多くのスラッシュコマンドが両方のインターフェースで共有されます。

| 操作                         | CLI                                           | メッセージングプラットフォーム                                                              |
| ------------------------------ | --------------------------------------------- | -------------------------------------------------------------------------------- |
| チャット開始                 | `hermes`                                      | `hermes gateway setup` + `hermes gateway start` を実行し、ボットにメッセージを送信 |
| 新しい会話を開始       | `/new` または `/reset`                            | `/new` または `/reset`                                                               |
| モデルを変更                   | `/model [provider:model]`                     | `/model [provider:model]`                                                        |
| 人格を設定              | `/personality [name]`                         | `/personality [name]`                                                            |
| 直前のターンを再試行または取り消し    | `/retry`、`/undo`                             | `/retry`、`/undo`                                                                |
| コンテキストを圧縮 / 使用量を確認 | `/compress`、`/usage`、`/insights [--days N]` | `/compress`、`/usage`、`/insights [days]`                                        |
| スキルを閲覧                  | `/skills` または `/<skill-name>`                  | `/<skill-name>`                                                                  |
| 現在の作業を中断         | `Ctrl+C` または新しいメッセージを送信                | `/stop` または新しいメッセージを送信                                                    |
| プラットフォーム固有のステータス       | `/platforms`                                  | `/status`、`/sethome`                                                            |

完全なコマンド一覧は、[CLI ガイド](https://hermes-agent.nousresearch.com/docs/user-guide/cli)と[メッセージングゲートウェイガイド](https://hermes-agent.nousresearch.com/docs/user-guide/messaging)を参照してください。

---

## ドキュメント

すべてのドキュメントは **[hermes-agent.nousresearch.com/docs](https://hermes-agent.nousresearch.com/docs/)** にあります:

| セクション                                                                                             | 内容                                             |
| --------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| [クイックスタート](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart)                 | インストール → セットアップ → 2 分で最初の会話          |
| [CLI の使い方](https://hermes-agent.nousresearch.com/docs/user-guide/cli)                              | コマンド、キーバインド、人格、セッション             |
| [設定](https://hermes-agent.nousresearch.com/docs/user-guide/configuration)                | 設定ファイル、プロバイダー、モデル、すべてのオプション                |
| [メッセージングゲートウェイ](https://hermes-agent.nousresearch.com/docs/user-guide/messaging)                | Telegram、Discord、Slack、WhatsApp、Signal、Home Assistant |
| [セキュリティ](https://hermes-agent.nousresearch.com/docs/user-guide/security)                          | コマンド承認、DM ペアリング、コンテナ分離          |
| [ツールとツールセット](https://hermes-agent.nousresearch.com/docs/user-guide/features/tools)            | 40+ のツール、ツールセットシステム、ターミナルバックエンド               |
| [スキルシステム](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills)              | 手続き的メモリ、Skills Hub、スキルの作成             |
| [メモリ](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory)                     | 永続メモリ、ユーザープロファイル、ベストプラクティス           |
| [MCP 統合](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp)               | 任意の MCP サーバーを接続して機能を拡張           |
| [Cron スケジューリング](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron)              | プラットフォーム配信付きのスケジュールタスク                     |
| [コンテキストファイル](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files)       | すべての会話を形作るプロジェクトコンテキスト             |
| [アーキテクチャ](https://hermes-agent.nousresearch.com/docs/developer-guide/architecture)             | プロジェクト構造、エージェントループ、主要クラス                 |
| [コントリビューション](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing)             | 開発セットアップ、PR プロセス、コードスタイル                  |
| [CLI リファレンス](https://hermes-agent.nousresearch.com/docs/reference/cli-commands)                  | すべてのコマンドとフラグ                                     |
| [環境変数](https://hermes-agent.nousresearch.com/docs/reference/environment-variables) | 完全な環境変数リファレンス                                 |

---

## OpenClaw または別のエージェントからの移行

OpenClaw、Claude Code、Codex CLI、Cursor から移行する場合、Hermes は設定、メモリ、スキルをインポートできます（OpenClaw の場合は、要求すれば API キーも）。

**セットアップ中:** `hermes setup` が別のエージェントからインポートするか尋ね、検出したもの（`~/.openclaw`、`~/.claude`、`~/.codex`、`~/.cursor`）を事前選択し、公式の `agent-importers` プラグインをインストールして、プレビュー付きでインポートを実行します。

**インストール後いつでも:**

```bash
hermes plugins install agent-importers          # プロファイルごとに 1 回
hermes import-agent openclaw                    # 対話型移行（完全プリセット）
hermes import-agent openclaw --dry-run          # 移行される内容をプレビュー
hermes import-agent openclaw --migrate-secrets  # 許可リスト済みの API キーも移行
hermes import-agent claude-code                 # または codex / cursor
```

OpenClaw からインポートされるもの:

- **SOUL.md** — 人格ファイル
- **メモリ** — MEMORY.md と USER.md のエントリ
- **スキル** — ユーザー作成スキル → `~/.hermes/skills/openclaw-imports/`
- **コマンド許可リスト** — 承認パターン
- **メッセージング設定** — プラットフォーム設定、許可ユーザー、作業ディレクトリ
- **API キー** — 許可リスト済みのシークレット（Telegram、OpenRouter、OpenAI、Anthropic、ElevenLabs）、`--migrate-secrets` 指定時のみ
- **TTS アセット** — ワークスペースの音声ファイル
- **ワークスペース指示** — AGENTS.md（`--workspace-target` 指定時）

`hermes claw migrate` は以前の表記として引き続き動作します。[OpenClaw 移行ガイド](https://hermes-agent.nousresearch.com/docs/guides/migrate-from-openclaw)と[他のエージェントからのインポート](https://hermes-agent.nousresearch.com/docs/user-guide/import-from-other-agents)を参照してください。

---

## コントリビューション

コントリビューションを歓迎します！開発セットアップ、コードスタイル、PR プロセスについては[コントリビューションガイド](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing)を参照してください。

アクティベーション、日常的な使用、依存関係の変更、環境の離脱については、[PM 開発者ワークフロー](website/docs/reference/package-management.md#developer-workflow)から始めてください。[開発セットアップ](CONTRIBUTING.md#development-setup)では、別のテスト環境と検証コマンドについて説明しています。

---

## コミュニティ

- 💬 [Discord](https://discord.gg/NousResearch)
- 📚 [Skills Hub](https://agentskills.io)
- 🐛 [Issues](https://github.com/NousResearch/hermes-agent/issues)
- 🔌 [computer-use-linux](https://github.com/avifenesh/computer-use-linux) — Hermes およびその他の MCP ホスト向けの Linux デスクトップ制御 MCP サーバー。AT-SPI アクセシビリティツリー、Wayland/X11 入力、スクリーンショット、コンポジタのウィンドウターゲティングを備えます。
- 🔌 [HermesClaw](https://github.com/AaronWong1999/hermesclaw) — コミュニティ製 WeChat ブリッジ: 同じ WeChat アカウントで Hermes Agent と OpenClaw を実行。

---

## ライセンス

MIT — [LICENSE](LICENSE) を参照。

[Nous Research](https://nousresearch.com) によって構築されました。
