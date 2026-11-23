# apps/desktop/src/ — バックエンド契約、スラッシュパレット、Bot モード

`apps/desktop/AGENTS.md`（判断ガイド）とルートの `AGENTS.md` の上に適用される。
ルートの TypeScript スタイル規則が適用される。

## デスクトップのローカル実行は正規のゲートウェイに属する

Electron + React + nanostores（`@assistant-ui/react`）は、既存の
`@hermes/shared` クライアントを介して JSON-RPC で通信する。通常のローカルプライマリ起動および
プール起動は `hermes gateway ensure --json` を呼び出し、その資格情報不要のエンドポイントを消費し、
新しいプライベート制御チケットで WebSocket を認証する。アプリはゲートウェイの PID を
所有子プロセスとして取得することはない。Desktop 接続を閉じる、切り替える、または追い出すと
ビューアが切断される。オーナーを停止するのは明示的なゲートウェイライフサイクルコマンドのみ。

ネイティブチケットはプライベートな preload IPC を一時的に通過し、WebSocket 構築前に URL から
削除され、サブプロトコルとして提供される。Electron は、要求元ウィンドウにバインドされた
未期限の一回限りのダイヤルに対してのみ Origin を削除する。公開ダッシュボードトークンは
スクレイプされず、公開接続記述子に追加されることもない。SSH/URL インテントは既存の
リモート解決と公開ライフサイクルを維持する。リモート障害でローカルオーナーを起動してはならない。

`gateway ensure` が接続するゲートウェイは、**ホームごとに 1 つの多重化オーナー**である。
`HERMES_DESKTOP=1` はアプリがそれを見つける方法ではなく、プロファイルごとの
`hermes serve --port 0` 子プロセスは生成されない。1 つのゲートウェイプロセスが複数のホームの
セッションにサービスを提供する（`tui_gateway/AGENTS.md` § プロファイルスコープ）。
サービス提供されるセカンダリは、多重化器の制御ソケット（`GatewayEndpoint.control_home`）を介して応答する。
リモート接続（SSH、URL+トークン、Cloud）も同様に、1 つのプロセスから複数のプロファイルに
サービスを提供するバックエンドに到達する。すべてのライフサイクル/ステータス/設定 REST 呼び出しは
`?profile=`（または `profile` パラメータ）を運び、すべての新規セッションタイルはオーナールートを記録する。
バックエンド側のスコープ修正は 2 回プローブされる — プロファイルをゲートウェイ自身の起動ホームとして、
および 1 つのプロセスによってサービス提供されるセカンダリとして。

この移行には、ランタイムの正規の GUI 作成ポリシーとプライベート HTTP API 資格情報パスが必要である。
欠落したランタイム機能を、GUI セッションを CLI として再ラベル付けしたり、起動オプションを
落としたり、独立したローカル serve オーナーにフォールバックしたりして回避してはならない。

## スラッシュコマンド: キュレーションはクライアント側、ディスパッチはバックエンドへ

- バックエンドはすでにすべてを提供している: `commands.catalog` と `complete.slash` は組み込み、
  ユーザー `quick_commands`、およびスキル由来のコマンドを含む。スキルを見るために新しい RPC は不要。
- `src/lib/desktop-slash-commands.ts` が要となるファイル: `DESKTOP_COMMAND_SPECS`（組み込みと
  そのデスクトップサーフェス）+ ブロックリスト。コマンドのデスクトップ上の扱い
  （ターミナルのみ / メッセージングのみ / 設定所有 / 上級 / 非表示）は、`hermes_cli/commands.py` の
  `CommandDef` に `desktop=` として **一度だけ** 記述される。ライブの `commands.catalog` がそれを運び、
  `src/lib/desktop-slash-registry.json`（`scripts/dump_desktop_slash_registry.py` で再生成;
  `tests/hermes_cli/test_desktop_slash_registry.py` + vitest ファイルがドリフト時に失敗する）が
  オフラインフォールバックである。Python レジストリが一度も知らない名前のみ
  （`/density`、`/details`、`/logs`、`/mouse` — Ink ローカル; `/pets`）が
  `TS_ONLY_NO_DESKTOP_SURFACE` に存在する。`isDesktopSlashCommand(name)` は **実行** をゲートする
  （組み込み AND 任意の非組み込みに対して true なので、型付きスキル/クイックコマンドが実行される）。
  `isDesktopSlashSuggestion(name)` は **発見** をゲートする — `app/chat/composer/hooks/use-slash-completions.ts` の
  両方の補完パスと `filterDesktopCommandsCatalog` の両方で使用される。
  `isDesktopSlashExtensionCommand(name)` は既知の組み込み以外のすべてに対して true であり、
  提案パスとカタログパスの両方が拡張を通す（許可リストはかつて、入力時に実行されたにもかかわらず
  すべてのスキル/クイックコマンドを補完から静かに落としていた）。
- ディスパッチ: `app/session/hooks/use-prompt-actions/slash.ts`（`runSlash`）— デスクトップ所有の組み込み
  （`/skin`、`/help`、`/new` など）をローカルまたは `commands.catalog` 経由で実行。それ以外は `slash.exec` →
  `command.dispatch` フォールバック。スキルコマンドは `{type: "skill", message}` に解決され、
  通常のプロンプトとして送信される。

**規則:** パレットのキュレーションはノイズ（ターミナルのみ / メッセージングのみの組み込み）を隠す。
ユーザー起動の拡張は決して隠さない。`desktop-slash-commands.ts` を厳格化する場合は、
`isDesktopSlashExtensionCommand` を両方のパスに流し続けること。テスト: `apps/desktop` から
`pnpm exec vitest run src/lib/desktop-slash-commands.test.ts`（ワークスペース依存関係はリポジトリルートでインストール）。

## Bot モード（`src/plugins/hermes-bots/`）— 1 ボット = 1 つの正規の永遠チャット、NAME で識別

各ボットは永続的なアイデンティティを持つ Hermes **プロファイル**である。この不変条件は繰り返し
退行し、そのたびにユーザーの会話履歴を失わせた。日常的な PR で再議論する余地はない。

チャットの唯一のアイデンティティは **（プロファイル、正確に「Bot Chat」と題されたセッション）** である。
状態 DB の UNIQUE(title) インデックスにより、そのペアは最大 1 行のレジストリになる。ボット行をクリックする:
1. **毎回レジストリを解決する:** `session.list {title, include_hidden: true}`（インデックス付き、
   ウィンドウなし。正規チャットは常に非表示なので非表示行も解決される。圧縮系統はライブの先端に解決される）。
   行が存在する → それを開く。それがハッピーパス全体である。
2. **行がない → 作成する**、`Bot Chat` と題し、非表示で生まれ、ボットのイントロで開始される。作成は
   ミント前に採用する: 最初にルックアップを再実行するので、並行/既存の行は開かれ、決してフォークされない
   （`set_session_title` は競合するタイトルを静かに落とす — 0 行を返す — これが
   2026-08 の無限フォークループが始まった方法である）。

**セッション ID ピンは存在しない。** 旧設計は `ui_meta['hermes-bots'].chat` にポインタを保存していた。
5 回のハードニングウェーブ（#88690、#90732、#90751、#91791 のリバート、#92042）はそれぞれ、
それがぶら下がるか盗まれる新しい方法を守っていた（rows[0] の盗用、`last_session` の採用、
一時的なクリア、cron セッションに再アンカーされたピン）。名前はぶら下がらない。ui_meta 内の
レガシー `chat` キーは無視され、破棄される。
**新しさが勝ってはならない**（#91791 → #92042）: 正規の Bot Chat は Sessions サイドバーから
無条件に非表示にされるので、ボット行が唯一の扉である — 「最も新しい可視セッションが勝つ」は、
1 つのセッションをプレビューし別のセッションを開く行の背後に関係全体を壁で囲む。
サイドチャット（「このエージェントと新しいチャット」）は配管タイトルではなく、サイドバーに
可視のままであり、行のターゲットになることは決してない。

レビュアーの帰結: ボットごとのセッションブラウザはない（#90732 で削除。戻さないこと）。
保存されたセッション ID ポインタを正規のアイデンティティとして拒否する — 「フォールバック層として」や
「検証のため」も含む。行のターゲットについて新しさ/可視性/「ユーザーが離れた場所」を参照するものは
すべて拒否する。そのような報告はサイドチャットに関するものであり、修正は Sessions サイドバーの
非表示スイープに属する。ゲートウェイはレジストリ行を `profiles.list` の `canonical_session` として報告する
（タイトルによってサーバー側で解決される）。ロスターのプレビュー、アクティビティシグナル、
`/new`→`/compact` ガードはすべてそれを読むので、プレビューのアイデンティティとクリックの
アイデンティティは構築上同じ行である。契約テスト:
`src/plugins/hermes-bots/` 内: `canonical-chat-registry.test.ts`（トリップワイヤー: オープンパスは
保存されたポインタを決して読み書きしない）、`canonical-chat-creation.test.ts`、
`canonical-chat-adopt-on-conflict.test.ts`、`bot-row-opens-canonical-chat.test.ts`、
`hide-bot-chats.test.ts`; さらにリポジトリルートの
`tests/tui_gateway/test_profiles_list_canonical_session.py`。

### グループチャット

[グループ契約](../docs/canonical-groups.md) に従う: ゲートウェイがそのメソッドをリストするときのみ
コントロールを提供し、生成された契約が宣言するものだけを送信し、クラシック実行にフォールバックせず、
ゲートウェイの `admitted: false` 証明があるときのみ Send の言葉を返す。

## 無料ティアのサーフェス（`src/store/free-tier*.ts`、Billing、ステータスバーチップ、オンボーディング準備画面）

`$freeTierStatus` は `free_tier.status` をミラーする（プル。ステータススナップショットと
サインイン後に更新される）。`deriveBillingView` は `logged_in` の **前** に `billing.free_tier_account` で分岐する
（ステータス `free_tier`: 通知 + 1 つのサインイン、Plan/Model/Connectors の要約、支払いまたは使用量の行なし）。
`logged_out` 通知のサインインは同じダイアログを開く。ポータルリンクは決して開かない
（リンクは資格情報を書き込まない）。サインインダイアログは単一の主張オーナーである
（最初のマウントが勝つ。実プロファイルの同意プロンプトと同様）。その状態はポールルートの
`status` + `reason` に 1:1 でマップされる。コピーは規則された無料ティアのコピーである:
ユーザー向けテキストで「guest」、「anonymous」、「claim」または「Nous Portal」を決して使わない。