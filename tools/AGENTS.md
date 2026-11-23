# tools/ + toolsets.py + model_tools.py — モデルツール

ルートの `AGENTS.md` の上に適用される。ここに何かを追加する前に、**Footprint Ladder** を確定させること。
ほとんどの機能はコアツールにすべきではない。長文形式: `website/docs/developer-guide/adding-tools.md`、
`tools-runtime.md`。

## レジストリとディスカバリ

`tools/registry.py` は依存関係を持たず、すべてのツールファイルからインポートされる。各 `tools/*.py` は
インポート時に `registry.register()` を呼び出す。`model_tools.py` はレジストリをインポートしてディスカバリを
トリガーし(`discover_builtin_tools()`)、その後 `run_agent.py`、`cli.py`、`batch_runner.py`、`environments/`
がそれを消費する。トップレベルの `registry.register()` を持つ `tools/*.py` は自動的にインポートされる —
手動のインポートリストは不要。パッケージ全体であるツール(`tools/connectors/`)は
`tools/<pkg>/tool.py` から登録される。これはパッケージ内でディスカバリがスキャンする唯一のファイルであり、
パッケージ内のすべての兄弟ファイルは構造上ライブラリとなる。パッケージには `__init__.py` が必要で、
これがないとディスカバリは警告付きでスキップする(setuptools はホイールからそれを除外するだろう)。
レジストリはスキーマ収集、ディスパッチ(`handle_function_call()`)、
可用性(`check_fn`、プロセス全体で TTL キャッシュ)、エラーラッピングを処理する。**すべてのハンドラは JSON
文字列を返す**。ただし、モデルにピクセルを渡すツールは例外で、マルチモーダルエンベロープ
`{"_multimodal": True, "content": [text, image_url…], "text_summary": str}` を返してもよい(`registry._normalize_handler_result`
はまさにその形状を受け入れる)。その画像パスは `vision_tools._native_tool_result_images` を通る —
プライベートなビジョンチェックは決して行わない。

## コアツールの追加（2ファイル）— ユーザーがコアツールを明示的に提供する場合のみ

カスタム／ローカルのみのツールではコアを編集しないでください。`~/.hermes/plugins/<name>/plugin.yaml` + `__init__.py` を作成し、`ctx.register_tool(...)` を呼び出してください。プラグインツールセットは自動的に検出され、`tools/` や `toolsets.py`（`plugins/AGENTS.md`）に触れることなく切り替えられます。

1. `tools/your_tool.py`:
   ```python
   from agent.secret_scope import get_secret
   from tools.registry import registry
   def check_requirements() -> bool: return bool(get_secret("EXAMPLE_API_KEY"))
   def example_tool(param: str, task_id: str = None) -> str: return json.dumps({"success": True, ...})
   registry.register(name="example_tool", toolset="example",
       schema={"name": "example_tool", "description": "...", "parameters": {...}},
       handler=lambda args, **kw: example_tool(param=args.get("param", ""), task_id=kw.get("task_id")),
       check_fn=check_requirements, requires_env=["EXAMPLE_API_KEY"])
   ```
2. `toolsets.py`: 名前を`_HERMES_CORE_TOOLS`（全プラットフォーム）または新しいツールセットに追加します。**必須**
   — ディスカバリはスキーマを登録しますが、ツールが公開されるのは、ツールセットがそのツールを名前指定した場合のみです。
   `_HERMES_CORE_TOOLS`は、各プラットフォームの基本ツールセットが継承するデフォルトのバンドルであり、デッドコードではありません。

ツールコードのルール:

- **スキーマの説明文で、他のツールセットのツール名を挙げてはならない**(ブラウザツールが「web_search を使うこと」など)。それらのツールは利用できない場合があり(キー欠落、ツールセット無効)、モデルがそれらへの呼び出しを幻覚する。相互参照は `get_tool_definitions()` で `model_tools.py` に動的に追加される — `browser_cdp` / `execute_code` の後処理ブロックを参照のこと。
- **スキーマ説明内のパスは `display_hermes_home()` を使う**(スキーマは import 時に構築される。multiplex 下では起動ホームが表示されるが、これは表示専用)。**状態ファイルは呼び出し時に `get_hermes_home()`** を使い、`Path.home()/.hermes` やモジュール定数は決して使わない。これにより、提供される各プロファイルがそれぞれ独自の状態を持つ。
- **指示系ツール(スキル、プロンプト、プレイブック)に `offset`/`limit` を付けない** — モデルは 1 ページ目を読んで残りを飛ばす(ルートのルール)。
- **`check_fn` は、それが実行されるプロファイルに対する到達可能性/オプトインに答えるものであり、サーフェス(表面)に対するものではない。** 結果は `registry.py::_check_fn_cache` に `hermes_home_key()` をキーとして TTL キャッシュされ、1 つのプロセスが多数のセッションと多数のプロファイルの両方にサービスを提供する。プローブは `agent.secret_scope.get_secret` を通じて資格情報を読み取るもので、素の `os.getenv` ではだめだ(それは起動プロファイルの `.env` を全員に返してしまう)。レジストリは `current_secret_scope()` からの `UnscopedSecretError` をキャッチ箇所で分類する — スコープのない起動時プローブはトレースバックではなく DEBUG である。GUI 専用ツールは名前付きツールセット(`desktop_ui`、`project`)に入れ、`_load_enabled_toolsets(platform)` によって組み込む(ルート: 能力は SESSION のプロパティである)。
- **エージェントレベルのツール**(`todo`、`memory`)は `handle_function_call()` の前に `INLINE_TOOL_EXECUTORS` テーブル(`agent/inline_tool_executors.py`; `agent/AGENTS.md`)によって傍受される。
- **`_last_resolved_tool_names`** は `model_tools.py` 内のプロセスグローバルである。`_run_single_child()` は `delegate_tool.py` 内で子の実行の前後でそれを保存/復元する — 読者は委譲の途中でそれが古くなっているのを見るかもしれない。
- 新しいツールは、生の環境変数ではなく、既存のセットアップ UX(`hermes tools`、`hermes setup`、自動インストール)と統合する。シークレットは `OPTIONAL_ENV_VARS`(`hermes_cli/AGENTS.md`)に入れる。

## ツールセット (`toolsets.py`)

単一の `TOOLSETS` dict。現在のキー: `browser, clarify, code_execution, cronjob, debugging,
delegation, discord, discord_admin, feishu_doc, feishu_drive, file, image_gen,
kanban, memory, messaging, moa, rl, safe, search, session_search, skills, terminal, todo,
tts, video, vision, web` (テストでリストをアサートしないこと)。プラットフォームごとの有効化/無効化は
`hermes tools` (curses) または config.yaml 内の `tools.<platform>.enabled/disabled` で行う。`browser_exec` は
主要なブラウザツールの1つ (`browser_cdp` / `browser_dialog` / `browser_vault` のほか、すべて CDP)。

## ブラウザランタイム

`browser_exec` (`browser_use_cli.py`) は、browser-harness を介して CDP でブラウザを操作します。その CDP エンドポイントの供給元は `browser_session.get_session_info(cache_key)` のとおりです。オペレーターの `BU_CDP_*` 環境変数（browser_exec 内）> CDP オーバーライド（ライブの `/browser connect` > `BROWSER_CDP_URL` > `browser.cdp_url`）> ハイブリッド `::local` サイドカー > クラウドプロバイダー（失敗時はローカルセッションを `fallback_from_cloud` とマーク）> ローカル。ローカル分岐はさらなるフォールバックの連鎖ではありません。`browser.use_real_profile` がオンの場合は同意済みの実プロファイルを試し、それ以外（同意オフ、プロファイルを読み込めない、Lightpanda のようなプロファイル非対応エンジン）では、実プロファイルを読み込まないブラウザを設定済みエンジンで実行します。デフォルトでは `browser_launcher.launch_chromium` の同梱 Chromium、`browser.engine: lightpanda` が設定されている場合のみ Lightpanda を使用します（自動で試されることはありません）。永続プロファイルが設定されている場合（`browser.user_data_dir`、Bot Desktop）を除き、そのブラウザはまっさらな状態です。キャッシュキーごとに 1 ブラウザ（`--remote-debugging-port=0` + `DevToolsActivePort`）。状態は `browser_session.py` に保存されます。起動されたすべての Chromium は親優先で停止され、プライベートな 0700 ディレクトリに記録されます（使い捨てプロファイルは `<HERMES_HOME>/cache/browser/chromium-records` 内、永続プロファイルは OS ユーザーごとにホストロックディレクトリ配下、それを固定する各ホームごとに 1 つ）。これにより、後続のプロセスが pid と開始時刻、およびその `--user-data-dir` argv トークンを確認したうえで、クラッシュしたオーナーのブラウザを回収します。リーパーは提供されるすべてのホームとすべての共有プロファイルを巡回します。`browser_tool.py` と `browser_tool_install.py` は凍結された旧アップデータのスタブのみです（それぞれの docstring を参照）。これらを拡張しないでください。

## tools/ 内のバックエンドとプロバイダー

いくつかのツールはプラグイン可能なバックエンドを前面に持つ。ターミナル環境（`tools/environments/`：local、docker、ssh、modal、daytona。`terminal_tool_backends.py`、`tool_backend_helpers.py`）、ブラウザ（`browser_launcher.py` + `browser_session*.py`：lifecycle、cloud、cdp、real_profile、sandbox）、MCPクライアント（`mcp_tool_*.py`：config、discovery、transport、registration、content、errors）、TTS（`tts_tool_providers.py`、`tts_command_provider.py`）、スキルハブのソース（`skills_hub_official.py`、`OptionalSkillSource`）。バックエンドの追加は、既存テーブルへの新しい兄弟エントリまたはプロバイダーエントリの追加であり、バックエンド名への`elif`を決して行わない（ルート形状のルール）。リモートバックエンドのファイル可視性の問題は、ツールを追加するのではなく、マウントで修正する。

**ネイティブビジョンの埋め込みは履歴であり、一回限りのペイロードではない。** `vision_tools.py::_vision_analyze_native`（および`browser_use_cli.py`内のブラウザスクリーンショットの双子）は、画像をツール結果に焼き込み、その後のAPI呼び出しごとに再送信される。サイズと繰り返しポリシーは`vision_tools_history_budget.py`（設定セクション`vision`：`embed_target_bytes`、`max_calls_per_image`）にあり、繰り返しカウンタは（セッションID、解決済みソース）をキーとするため、領域クロップはそのファイルのカウントを共有し、そのデフォルト上限は`agent.delegation_context.is_delegated_child_process_context()`内でのみ適用される。新しい埋め込みコストのルールはそこに置き、ツール内に2つ目のカウンタを決して作らない。

**すべての spawn は 1 つの env ビルダーを通る。** `environments/local.py::build_subprocess_env`（+ `hermes_constants.apply_subprocess_home_env`、`env_passthrough.py::resolve_passthrough_value`）が、ターミナル、`execute_code`、バックグラウンドプロセス、委譲子プロセス、ACP または MCP stdio 子プロセスが環境を取得する方法である。提供されたプロファイルに代わって動作する子プロセス（`hermes -p X` ワーカー、`key_cmd` ヘルパー、ブラウザドライバ、Bot Chat リレーターン）は `environments/local.py::
served_profile_child_env(target_home=, inherit_credentials=)` を使用する。起動プロファイルの `.env` / `TERMINAL_*` の残骸は破棄され（`strip_launch_profile_env`）、対象のホームが固定され、対象自身のシークレットだけが重ね合わせられる。`os.environ.copy()` / `dict(os.environ)` は起動プロファイルを固定する。contextvars はプロセス境界を越えないため、`Popen` の前に解決する。子プロセスの `UnscopedSecretError` は spawn サイトのバグであり、environ のフォールスルーを追加する理由にはならない。スコープ付きコードからの新しいスレッドは `agent.memory_provider.spawn_context_thread` を使用する（素の `threading.Thread` はスコープを失わせる）。**MCP の信頼はプロファイルごとのレコードである。** `mcp_tool_registration.py::
_record_scope_trust` はホームを基準に信頼をキー付けする。セカンダリは同名サーバーに対して起動プロファイルの信頼を採用せず、`mcp_tool_handlers.py::_trust_gate_check` は呼び出し元セッションのプロファイルを参照する。

**バックグラウンドプロセスの終了処理は、まず親プロセスにシグナルを送る。** `process_registry_termination.py::
ProcessTerminationMixin._terminate_host_pid` は子孫プロセス群のスナップショットを取り、記録された親プロセスにのみ SIGTERM を送り、`terminal.daemon_term_grace_seconds` その終了を待って自身の子プロセスを回収（reap）し、その後スナップショット内の生存プロセスに SIGTERM を送り、両方を無視したプロセスには SIGKILL を送る（これにより、自身のプロセスツリーを回収するスーパーバイザー——Chromium/Electron ブラウザが zygote を回収する場合や、シェルの trap など——はクリーンに終了する一方、子プロセスが SIGHUP を無視するシェルでも孤児プロセスを残さない）。子孫プロセスに親より先に SIGTERM を送ってはならない。ブラウザの zygote をシャットダウン中に殺すと、終了コード 0 が SIGTRAP のコアダンプに変わる。`_stop_systemd_unit`（スコープの終了処理で、ワーカー cgroup を kill する）は、`kill()` におけるその PID kill の後、または既に死んでいる／再利用されたと確認された親に対してのみ実行される（`session.exited`、`_signal_kill` の PID 再利用経路、チェックポイント復旧）——生存中の親が最初に受け取るシグナルがこれになることは決してない。

## 委譲（`tools/delegate_tool.py`）

サブエージェントを、分離されたコンテキストとターミナルセッション付きで生成します。親はサマリーを待ちますが、`background=true` の場合は委譲IDを返し、非同期委譲完了キュー経由で結果を再取得します。形状は、単一（`goal` + 任意の `context`、`toolsets`）またはバッチ（`tasks: [...]`、並行数は `delegation.max_concurrent_children` で上限、デフォルト3）です。バックグラウンドバッチはデフォルトで1つの完了として返ります。`delegation.independent_completions` を指定すると、完了**ユニット**（`delegate_tool_dispatch._units_of`）に分割されます。`group` を共有するタスクは結合してまとめて報告し、グループ化されていない各タスクは完了時に単独で報告します。このバリアントのスキーマは、タスクごとに `group` を必須（`_build_dynamic_schema_overrides`）としてマークするため、モデルは毎回の呼び出しで配送の選択を明示します。ハンドラーはこれを強制しません。1回の呼び出しのユニットは1つのプールスロットを共有します（`slot_key`、`async_delegation._dispatch`内）。ユニットを容量として数えることは決してしないでください。実行エグゼキュータは生存中のユニット数でサイズ調整され、ストールクロックはランナー起動時に作動するため、キューに入ったユニットがストールと判定されることはありません。ロール: `leaf`（デフォルト。`delegate_task`、`clarify`、`memory`、`send_message`、`cronjob` なし。`execute_code` を保持）と `orchestrator`（`delegate_task` を保持。`delegation.orchestrator_enabled` でゲートされ、`delegation.max_spawn_depth` で上限、デフォルト2）。`delegation:` 配下の設定ノブ: `max_concurrent_children, independent_completions, gateway_mode, max_spawn_depth, child_timeout_seconds, orchestrator_enabled,
subagent_auto_approve, inherit_mcp_toolsets, max_iterations, backend, backends`。**ルート:** `delegation.backend` は委譲プロバイダー（`agent/delegation_provider.py`、`ctx.register_delegation_provider`。その設定は `delegation.backends.<name>` にあります）を選択し、各タスクのルートに応答します（`tools/delegate_tool_routes.py`: モデル/プロバイダーフィールドは `delegation` セクションと同様に解決され、`service_tier` は `/fast` 内の `delegate_tool_tuning.py` と同様にチェックされ、または `profile` → 子が構築され、そのプロファイルのスコープ内でリースと会話を行います）。また、enum検証済みのタスク別スキーマパラメータを追加できます。ライフサイクルは所有しません。`default` 戦略はバンドル済みの `plugins/delegation/default` プラグインです（選択する以外にコアの特別扱いはありません）。フェイルクローズ: 使用不能なバックエンドは、それを名指しするツールエラーになります（決して黙って `default` にはしません）。ルーティング不能なタスクは単独で拒否され（`TaskRoute.error`）、バックエンドが持たないパラメータを送るタスクも同様です。セッションは、その `delegate_task` が構築されたバックエンド上でルーティングされます（`agent._delegation_backend`、そのツールで固定）。したがって、保存は `/new` または `--now` で適用されます（`agent/delegation_backends.py`）。内部の `credentials_cfg` 呼び出し元（/review）とライフサイクルAPIはこれをバイパスします。**子プロセス:** 子のバックグラウンドプロセスは、そのティアダウン時に強制終了され、その通知は親で抑制されます。`process_manage(action="handoff")`（子のみ）は、レジストリロック下で `ProcessSession.owner_task_id` を親に切り替え（`process_registry.transfer_ownership`）、完了が新しい所有者によってルーティングされ回収されるようにします。引き取り手のない残り物は結果上で `orphaned_processes` となり、終了したが一度も読まれていない通知プロセスは `unread_completions` となります（`_ChildRun.account_background_processes`、`cleanup` がそれらを強制終了する前）。**子カーネル:** 子の `execute_code` カーネルは `<parent-owner>::child::<child-session-id>` でキー付けされ、子の実行中は `max_session_kernels` LRU上限に対して固定され、`cleanup` によって破棄されます（`code_kernel.shutdown_kernels_for_delegated_child`）。終了した子のカーネルに上限を占有させないでください。**output_schema:** 1回のリトライ後のミスは、`status: completed` を生テキストとともに `summary` に保持し、さらに `schema_valid: false` / `schema_errors` / `schema_note` を保持します。子の結果を決して破棄しないでください。**耐久性:** バックグラウンド委譲はプロセスローカルです。再起動後も存続させる必要がある作業には `cronjob` または `terminal(background=True, notify_on_complete=True)` を使用します。同じスパーン上の `heartbeat=N` は `heartbeat` イベントを発行します（完了キュー上の型。デルタ出力のみ、`HEARTBEAT_MIN_SECONDS` 下限、`process_registry.py::ProcessRegistry._heartbeat_loop` 内の全セッションに対して1つのデーモンタイマースレッド）。`watch_match` を描画するすべてのサーフェスは `heartbeat` を描画する必要があります（`process_registry_notifications.py`、`gateway/run.py::_drain_gateway_watch_events`、`tui_gateway/session_notifications.py::_DEDUP_EXTRA_FIELDS`）。**停止ファンアウト:** ターンのハード割り込みは `_active_children` にのみ到達します。バックグラウンドユニットはディスパッチ時に切り離され、意図的にそれを生き延びます（Teknium の裁定: バックグラウンドサブエージェントは、`/review` を含め、それを生成したチャットから独立しています）。ターン停止 — Ctrl+C、Esc、Desktop/TUIの停止ボタン、割り込むメッセージ、`session.interrupt`、ACP `cancel` — は決して `async_delegation.interrupt_for_session` を呼び出しません。明示的な `/stop` コマンド（ゲートウェイのビジーおよびアイドルパス、CLIおよびDesktopのプロセス停止）とセッションのクローズ/リセットだけがそれらを終了します。深度>0の委譲は常に同期です（`_model_background_value`）。したがって、停止は子自身の `_active_children` ファンアウトを再帰します。割り込まれたエントリの `summary` は、子の最後の実際のアシスタントテキストです（`_build_result_entry`）。API: `website/docs/developer-guide/subagent-lifecycle-api.md`。

## テスト

`tests/tools/`。ハンドラーは単体関数としてではなく、レジストリ経由（実際のディスパッチ）でテストする。ツール数のカウントではなく、契約（「登録されたすべてのツールにツールセットがある」「スキーマの説明が別のツールセットのツールを参照していない」）を検証する。承認・セキュリティ境界のツールは、一時的な `HERMES_HOME` に対して実際のインポートを使ったE2Eテストを行う（`tests/tools/test_approval_config_readonly.py` を参照）。

## サーフェス機能はプロセス環境ではなくセッションのプロパティである

*相手が誰であるか*（デスクトップペイン、アプリ内ブラウザ、メッセージリアクション、Projects）だけに依存して動作するツールは、バックエンドの環境変数からではなく、**セッション自身のソース**から利用可能性を解決しなければならない。クライアントとバックエンドは別々のマシンである。デスクトップアプリはローカルで起動されたバックエンド、SSH経由のバックエンド、URL＋トークンの背後にあるバックエンド、またはHermes Cloudを駆動する可能性があり、`HERMES_DESKTOP=1`を保持するのは最初の2つだけである。環境変数キーによるゲートは、他のトポロジでは無言のノーオペレーションとなる。プラットフォームのヒントがモデルに「Hermesデスクトップアプリ内にいる」と伝えている一方で、ツールはスキーマから取り除かれる。パターンは以下の通りである。

- **ツールセットはサーフェス（表示面）のゲートである。** そのようなツールを `_HERMES_CORE_TOOLS` から外し、名前付きツールセット（`desktop_ui`、`project`）に置くこと。GUI ゲートウェイの `_load_enabled_toolsets(platform)` は、セッションのプラットフォームが GUI を示す場合にそれを組み込む。リゾルバは1つ、トポロジはすべてに対応する。

- **`check_fn` が答えるのは到達可能性またはオプトインであり、サーフェスではない。** 「ブリッジは配線されているか？」——それは良い。 「私は Electron から生成されたか？」——それは違う。 `check_fn` の結果はプロセス全体で TTL キャッシュされる（`tools/registry.py`）。セッションごとの回答はそこに属さない。

- **どのアイデンティティを指すのかを問え。** `HERMES_DESKTOP=1` は正当に「このバックエンドはアプリによって生成された」を意味する（cron ティッカー、web-dist の処理）。それは「GUI が監視している」を意味しない。埋め込みターミナルペイン（そのバックエンドに対する `hermes --tui`）が反例である。

テスト: クライアントが別のマシンにあってもその機能が依然として意味をなすなら、それはセッションスコープである。GUI セッションが **env 変数が存在しない状態で** そのツールを取得することを検証せよ。
