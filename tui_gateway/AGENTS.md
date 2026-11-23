# tui_gateway/ + ui-tui/ — TUIとそのJSON-RPCバックエンド

ルートの`AGENTS.md`の上に適用されます。TUIは従来のprompt_toolkit CLIを完全に置き換えます。
`hermes --tui`または`HERMES_TUI=1`で有効化します。`tui_gateway`は、デスクトップアプリと
ダッシュボード`/chat`が通信するバックエンドでもあります。ここでの変更には3つの利用者がいます。

## プロセスモデル

```
hermes --tui
  └─ Node (Ink)  ──WebSocket /api/ws, hermes-gateway-v1──  the profile's gateway owner
       │  (URL + single-use ticket:                              ├─ session authority: sessions, AIAgent, tools
       │   ui-tui/scripts/gateway_bootstrap.py)                  └─ tui_gateway handlers (non-session methods)
       └─ renders transcript, composer, prompts, activity
```

インクはプロフィールの共有ゲートウェイオーナー（`hermes gateway run`、アイドル終了時にオンデマンドで起動）に接続され、プライベートな子には決して接続されません。`ui-tui/scripts/gateway_bootstrap.py`は`hermes_cli/gateway_runtime_attach.py::attach_gateway`の薄いラッパーであり、`hermes gateway attach
--json`が他のローカルクライアントに与える接続です。別のURLをダイヤルするのは`HERMES_TUI_GATEWAY_URL`（ダッシュボードの`/chat`）だけであり、そのリスナーのreadyフレームからワイヤをネゴシエートします。

TypeScriptが画面を所有します。Pythonがセッション、ツール、モデル呼び出し、スラッシュコマンドのロジックを所有します。エージェントの振る舞いをレンダラーに移動させてはいけません。

## Transport

WebSocket（`/api/ws`、`tui_gateway/ws.py`）または stdio（`tui_gateway/entry.py`）を介した、改行区切りの JSON-RPC フレームによるピアツーピア通信。オーナーのチケット付きソケットでは、セッションメソッド（下記の `hermes-gateway-v1` `CANONICAL_METHODS`）はセッション権威へ送られ、その他のメソッドがこれらのハンドラに到達するのは完全な対話的許可（`ws_legacy_fallback.py`）がある場合のみ。クライアント→サーバーのメソッド呼び出し、サーバー→クライアントの **リクエスト**（エージェントがユーザーに何かを尋ねるもの：`approval`、`clarify`、`sudo`、`secret`、`vault.*`、`connection`、デスクトップの読み取り／操作ブリッジ）、およびサーバー→クライアントの `event` 通知。`tui_gateway/server.py` はメソッド／イベントのカタログを持つファサードで、メソッドは `methods_*.py` の兄弟（`methods_config`、`methods_complete`、`methods_browser`、`methods_bot_relay`、...）に、イベント公開は `event_publisher.py` / `event_replay.py` に、サーバー→クライアントのリクエストは `server_requests.py` に存在する（`send()` は、同じ `srq-<n>` id を持つレスポンスフレームが届くまでエージェントスレッドをブロックし、`cancel*` は `request.cancel` イベントで取り下げ、`open_requests(sid)` は `session.resume` / `session.events.since` が再生するもので、再接続したクライアントがまだ開いている質問を再描画できるようにする）。クライアントは接続ごとに一度、それらに応答することを宣言し（`client.capabilities {server_requests: true}`、共有チャネルが `gateway.ready` で送信）、一度も宣言しなかった WebSocket クライアントはサーバー→クライアントのリクエストより古いアプリビルドであり、その場合 `send()` はエージェントを期限まで停滞させる代わりに即座に失敗する。デスクトップは `apps/shared`（`JsonRpcGatewayClient`、`onRequest`）を介して WebSocket で同じサーバーに到達する。新しい RPC は、新しい `methods_<topic>.py` か、既存のトピック別兄弟へのエントリを追加し、テーブルに登録する——`if method == ...` チェーンは不要（ルート形状の規則）。

**ワイヤはPythonで宣言され、TypeScript向けに生成される**（`tui_gateway/contracts/`）。すべてのメソッドに`Params`と`Result`のモデルがあり、すべてのサーバー→クライアント要求に`Params`と`Result`、すべてのイベントに`Payload`がある。それぞれ1つのPydanticクラスで、デフォルトでは`extra="forbid"`（プロデューサー所有のdictには`OpenModel`）。`register_method`はインポート時に未宣言の名前を拒否し、ディスパッチャは未知のパラメータキーを拒否する（`4000`＋キーパス）。さらに`HERMES_TEST_ISOLATION=1`の下では、ハンドラの結果または送信されたペイロードがそのモデルと一致しない場合に`ContractViolation`を送出する（本番環境ではログのみ）。`apps/shared/src/
gateway-contract.generated.ts`（`RpcMethods`、`ServerRequestMap`、`BackendGatewayEventMap`＋すべての値の形状）と`gateway-contract.openrpc.json`は`scripts/gen_gateway_contracts.py`によってレンダリングされ、`tests/tui_gateway/contracts/test_generated.py`はそれらが古くなっていると失敗する。したがってループは次のとおり：モデルを変更する→再生成する→`tsc`がすべてのコンシューマーにフィールドが移動したことを示す。`apps/shared/src/gateway-events.ts`は、クライアントローカルの合成イベントと`GatewayEvent`エンベロープをその上に追加するだけである。

ネイティブの`hermes-gateway-v1`トランスポートには、`contracts/canonical*.py`内に別の`CANONICAL_METHODS`カタログがあり、`canonical_method(...)`で宣言される。`gateway/session_controls.py::
AuthorityConnection`はパラメータと成功結果をそれに対して検証し、未知または欠落したパラメータキーは`4001 invalid_params`を返す。スタンドアロンモデルを再利用するのは、そのワイヤが同一の場合のみ：共有メソッド名が異なるスナップショット、入場受理、プロデューサー結果を運ぶことがある。同じジェネレータが`CanonicalRpcMethods`とOpenRPCの`x-canonical-methods`を、`RpcMethods`を広げることなく生成する。`tests/gateway/test_canonical_wire_contract.py`はハンドラのカバレッジを検査する。

名前が実行時にのみ存在するメソッドファミリー（`plugin.<plugin_id>.<name>`）は、`CANONICAL_NAMESPACES`内の1つの`canonical_namespace(...)`エントリになる：パターン、プレフィックス、オープンパラメータ、そしてクライアントがゲートする`runtime.describe`機能（`CanonicalRpcNamespaces`／OpenRPCの`x-canonical-namespaces`）。

ユーザーへの新しい質問＝エミッタ内の`_ask("<method>", sid, params, timeout)`、`apps/desktop/.../gateway-event/server-requests.ts`と`ui-tui/src/app/createServerRequestHandler.ts`内のハンドラ、および`contracts/server_requests.py`内の`server_request(...)`。

新しいイベント＝`contracts/events.py`内の`event("<type>", Payload)`。エミッタはそれに対して検査される。

## RPCメソッドにおけるプロフィールのスコープ

1つの `serve` プロセスが、複数のプロファイルホームのセッションをホストすることがあります（Desktop のプール型バックエンドはプロファイル配下で起動され、ダッシュボードは複数を提供します）。起動プロファイルはプロファイルであり、「default」は起動ホームを意味し、決して `~/.hermes` ではありません。ホストされる最初の非起動ホームが `launch_profile_policy.py` を `set_multiplex_active(True)` に切り替えます。これが無いと、すべてのフェイルクローズ型ガードが暗黙に無効になります。

ホーム・設定・`.env` 由来の状態を読み書きするすべてのメソッドは、`server.py::@_profile_scoped`（ライブセッションの `profile_home`、またはセッションレス呼び出しの場合は明示的な `profile` 引数から解決）の下で実行され、ツール・エージェント構築では `methods_tools.py::_profile_scoped_rpc` の下で実行されます。トークンは `model_switch.py::
_profile_runtime_scope_tokens(profile_home)`、つまりホーム＋シークレットスコープ＋ターミナルスコープを合わせたものから得られます。

**`get_hermes_home_override()` のみを設定するメソッドは半分しかバインドされていません**。設定パスは正しいプロファイルに解決される一方、資格情報と `TERMINAL_*` ポリシーは依然として起動プロファイルから取得されます。

ターン外のパスも同じようにバインドされます。`session_lifecycle.py::_finalize_session` / `_teardown_session` は `on_session_end` を囲む `_session_profile_runtime_scope(session)` に入り、メモリコミットと `agent.close()` も同様です（これらの呼び出し元はスコープ外のリーパー、タイマー、atexit、プールスレッドです）。バックグラウンドスレッドは `agent.memory_provider.spawn_context_thread` 経由で開始し、素の `threading.Thread` は使わないでください。子プロセスは `tools/environments/local.py::served_profile_child_env`（`hermes -p X` ワーカー、`key_cmd` ヘルパー、ブラウザドライバ）を通じて提供対象プロファイルのために動作し、`dict(os.environ)` は使わないでください。

追加する前にスコープ外のハンドラを探してください。`tui_gateway/` 内の `file_glob="methods_*.py"` を持つ `^(async )?def ` に対する `search_files`、`context=1` を確認し、それぞれについて `_profile_scoped` を検査してください。2つのオンディスクホームと、セカンダリにのみ存在する `.env` 名でプローブします。そのセッションに対してメソッドを呼び出し、セカンダリの値が解決され、起動プロファイルの値が解決されないこと、およびその後 `os.environ` が変わらないことを検証してください。

## 主要なサーフェス

| サーフェス | Ink コンポーネント | ゲートウェイのメソッド / イベント |
|---|---|---|
| チャットのストリーミング | `app.tsx` + `messageLine.tsx` | `prompt.submit` → `message.delta` / `message.complete` |
| ツールのアクティビティ | `thinking.tsx` | `tool.start` / `tool.generating` / `tool.complete` |
| 承認 | `prompts.tsx` | サーバー→クライアントのリクエスト `approval` → レスポンス `{choice}` |
| 明確化 / sudo / シークレット | `prompts.tsx`, `maskedPrompt.tsx` | サーバー→クライアントのリクエスト `clarify` / `sudo` / `secret` (`server_requests.py`) |
| セッションピッカー | `sessionPicker.tsx` | `session.list` / `session.resume` |
| スラッシュコマンド | ローカルハンドラ + フォールスルー | `slash.exec` → `_SlashWorker` (`slash_worker_client.py`); `command.dispatch` |
| 補完 | `useCompletion` フック | `complete.slash`, `complete.path` (非ローカルの `terminal.backend` の下では、`complete.path` がセッションのターミナルバックエンドを通じてディレクトリを一覧表示します。ゲートウェイホストは同名のツリーが正しく見えても誤りとなるため、決して使用しません) |
| テーマ | `theme.ts` + `branding.tsx` | `gateway.ready` がスキンデータを運びます |
| 接続操作（デスクトップカード） | デスクトップ `store/connection-request.ts` | `connection.request` → `connection.update`* → `connection.respond {op_id}`; `connectors.operation.status`。この操作は `tools/connectors/live.py` に存在し、カードはツールスレッドをパークしません (`methods_connectors.py`)。 |

## 共有サブエージェントのスナップショット

`subagent.list({session_id})` は、呼び出し元トランスポートのライブセッションに対して `{subagents, delegations}` を返します。ロスターは読み取り専用で、CONVERSATION に従います。つまり、正確なオーナーレコードと、その永続的な系統（`owner_agent_session_id` → 圧縮チップ。プロセス内の `delegate_task(action="list")` と同じスパイン）がセッションのエージェントである子レコードです。これは、Desktop の再接続／再開が UI セッション ID を再発行し、圧縮がキーをローテーションする一方で、子は実行を継続するためです（#114909）。制御（`steer` / `interrupt` / `tail`）は、正確なセッションレコードとトランスポートに固定されたままです。子の権限は RPC 時に、所有セッションの LIVE トランスポートスロットに対して解決されるため、認証済みの再接続経路（prompt.submit、キューのドレイン、resume、activate、ビューアのフェイルオーバー）はすべて、レジストリの簿記なしでそれを保持します。アタッチ箇所にレコード単位のトランスポート同期を追加してはなりません。外部または退避した世代は制御不能のままです。`last_tool` は最後に開始されたツールであり、実行中を示すものではありません。非同期完了ユニットはエージェントではなく、正確な世代権限を持ちません。`delegations` はワイヤ互換性のため空の配列のままです。ディスパッチコンテキスト、結果、コールバック、ルーティングキーは送信されません。クライアントはこのスナップショットから既存のポーリングでハイドレートし、変更がない場合は更新を回避します。

`subagent.tail({session_id, subagent_id})` は `{subagent_id, available, text, truncated}` を返す。
実行中の子エージェントの既存の会話履歴から、末尾16 KiBを取得する。ポーリングするのは選択中の詳細だけ。
子が存在しない、終了済み、または別の所有者に属する場合は、利用不可を示す空のスナップショットを返す。
クライアントから渡されたパスは開かない。この RPC は実行中の情報だけを扱い、永続化済みの完了履歴は扱わない。
セッションまたはトランスポートが無効ならエラー4001を返す。子の保存済み行は、実行中・終了済みを問わず、
正規の所有者の `session.transcript` から `subagent_id` を付け、カーソルを指定して取得する。
一覧の行には、両方のトランスポートで子の `child_session_id` が入る。
共通の制御は引き続き `subagent.steer({session_id, subagent_id, text})` を使う。
`status: queued` は受付を示す。配信完了は保証しない。終了境界で競合した場合は、既存のランタイムが
`missed_steer` として報告する。
`subagent.interrupt({session_id, subagent_id})` は、子孫も含め、実行中のセッション、トランスポート、世代の
所有権が完全に一致することを要求する。RPC セッションの権限がなければ拒否する。プロセス内で直接呼ぶ
`interrupt_subagent(id)` は、スコープを限定しない従来の契約を維持する。

## スラッシュコマンドの処理

1. クライアント組み込みのコマンド（`/help`、`/quit`、`/clear`、`/resume`、`/copy`、`/paste` など）は
   `app.tsx` がローカルで処理する。
2. その他は `slash.exec` に渡し、常駐する `_SlashWorker` サブプロセスで実行する。フォールバックの
   `command.dispatch` で、ゲートウェイがスキル、エイリアス、実行ディレクティブに解決する。
   スキルコマンドは `{type: "skill", message}` に解決し、通常のプロンプトとして送信する。


`commands.catalog`（空クエリリスト）には、組み込み、ユーザー `quick_commands`、プラグインコマンド、およびスキル由来のコマンドが含まれます。`complete.slash` は既存の CLI コンプリーター（レジストリ、プラグイン、スキル/バンドル、引数補完）を使用し、クイックコマンドはカタログのみに留まります。共有データビルダーは `tui_gateway/command_discovery.py` にあり、レガシーサーバーをインポートしません。定義は `hermes_cli/commands.py`（`hermes_cli/AGENTS.md`）から取得されます。

正規のゲートウェイは、`gateway/session_discovery.py` を通じて同じ2つのディスカバリー RPC を公開します。ディスカバリーの前に、認証済みの `session:read` 機能と、権限元の正確なプロファイルが必要です。任意の名前付き `profile` は、その同じホームに解決される必要があります。外部セレクターは `profile_mismatch` を返します。ディスカバリーは、権限元のプロファイルスコープ内でループ外で実行され、レガシーセッションや実行ランタイムを作成しません。カタログの警告、カテゴリ、エイリアス、デスクトップメタデータ、スキルの使用状況/由来、および補完置換オフセットは、レガシー形式を維持します。ディスカバリーは、リストされたすべてのスラッシュ実行コマンドが正規の RPC によって実装されていることを保証するものではありません。

## 正規のローカルスラッシュ実行

`gateway/session_commands.py` は、レガシーサーバーやスラッシュワーカーを読み込むことなく、`slash.exec({session_id, command})` と `command.dispatch({session_id, name, arg})` の両方に適応します。任意の `profile` は、権限者の正確なプロファイルを指定する必要があります。ディスパッチできるのは、認証されたアクターに属するサーバー登録済みのローカルソースのみです。呼び出し元が指定したソース、ルーティング、認証情報、またはプラットフォームのフィールドは拒否されます。

レビュー済みのゲートウェイハンドラー: `help`、`commands`、`status`、`context`、`version`、`whoami` は `session:read` を必要とします。`title` は `session:control` を必要とします(そのクエリ形式を含む)。レジストリのエイリアスは受け入れられます。既存のレジストリのビジー拒否およびターン途中のディスパッチポリシーが適用されます。結果は `{type: "exec", output}` です。

プロファイルスキルと、これらのコマンド/スキルに設定されたクイックコマンドエイリアスがサポートされます。スキルの解決には `session:submit` が必要で、既存の `{type: "skill", name, message, display}` ディレクティブを返します。Desktop と Ink はすでにそのメッセージを `prompt.submit` 経由で送信しており、独自の永続的な入力 ID を保持しています。解決自体はターンを開始せず、キャッシュされたシステムプロンプトも変更しません。通常の永続的な受け入れ経路が FIFO、リトライ、承認、実行を管理します。

`type: exec` クイックコマンドとプラグインのスラッシュコマンドには `session:control` が必要で、メッセージングゲートウェイ自身のディスパッチを通じて実行されます（`gateway/run_inbound_hooks.py`：スラッシュアクセスポリシー、出力を秘匿化した30秒のサニタイズ環境での実行、プラグインセッション環境）。その他のコマンドはすべて `unsupported_command` を返します。バンドル、ランタイム／設定の変更、承認・秘密情報のスラッシュショートカット、ライフサイクルコマンドを含みます。利用可能な場合は既存の世代バインド制御RPCを使用してください。カタログに存在するだけでは実行サポートを意味しません。正規のトランスポートにはレガシーフォールバックはインストールされていません。

## 正規のネイティブプロジェクション

`gateway/session_config.py` は、共有プロバイダーインベントリを通じて、プロファイル認可済みの `config.get` プレゼンテーション読み取りと `model.options` を公開します。`full` には、表示・承認・貼り付けの設定に加えて、音声の録音・送信設定が含まれますが、プロバイダー／MCP／プラグインの認証情報は含まれません。セッションの推論・モデル選択は、保持されたエージェントまたは凍結された起動ポリシーから取得されます。`mtime.mcp_rev` はそのポリシーに固定されます。外観上の編集はキャッシュを破壊するライブMCPリロードを要求しません。ビジー状態のオーバーライドはセッションスコープのままです。コンポーザーのモデル変更には `session.mutate` を使用し、グローバルな `config.set` は使用しないでください。ディスカバリはプロバイダーメタデータを更新できますが、推論を開始することはありません。

## 開発コマンド

```bash
cd ui-tui
pnpm install       # first time
pnpm run dev       # watch mode (rebuilds hermes-ink + tsx --watch)
pnpm start         # production
pnpm run build     # full build (hermes-ink + tsc)
pnpm run typecheck # tsc --noEmit
pnpm run lint      # eslint
pnpm run fmt       # prettier
pnpm test          # vitest
```

リポジトリのルートから、`just tui` で同じウォッチモードが実行されます。

Python テスト: `tests/tui_gateway/` を `scripts/run_tests.sh` 経由で実行します。TS テスト: `ui-tui` 内の vitest を使用します。`package.json` / `.ts` のソースについて検証する Python テストは、JS のみの PR では実行されません。JS 側の検証は vitest 側に置いてください（ルートのテスト規則）。ルートの TypeScript スタイル規則が適用されます。

関連: `web/AGENTS.md`（ダッシュボードはこの TUI を PTY 経由で埋め込みます）、`apps/desktop/AGENTS.md`（同じバックエンド上で独自のレンダラーを使用します）。
