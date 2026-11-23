# hermes_cli/ + cli.py — CLI、スラッシュコマンド、設定、スキン、アップデーター、プロファイル

ルートの `AGENTS.md` の上に適用されます。長形式: `website/docs/developer-guide/cli-internals.md`。

## CLIアーキテクチャ

`cli.py` は `HermesCLI`（REPLループ、設定、スラッシュディスパッチ）を保持し、振る舞いはミックスイン
`hermes_cli/cli_commands_mixin.py`、`cli_stream_mixin.py`、`cli_status_bar_mixin.py`、
`cli_billing_mixin.py`、`cli_tui_mixin.py`（ウィジェット、キーバインディング、パネル）、`cli_tui_runtime_mixin.py`
（実行ループのフェーズ: 入力ディスパッチ、起動、シグナル、シャットダウン）、`cli_init_mixin.py`（`__init__`
フェーズ）にあります。... モジュールレベルのヘルパーは、`cli.py` が再エクスポートするトピック別の兄弟モジュールにあります:
`cli_config_load.py`（デフォルト値 + YAMLマージ、環境変数ミラーリング）、`cli_render.py`（ANSI/スキン色、
ライトモード、マークダウン、`_cprint`、パネル折り返し）、`cli_terminal_input.py`（ファイルドロップ、ペースト/Enterキー
シーケンス、CPRガード）、`cli_shutdown.py`（終了ウォッチドッグ、クリーンアップ手順、一回限りのファイナライズ）、
`cli_single_query.py`（`-q` ランナー、終了コード、かんばんループ）、`cli_auto_maintenance.py`（状態DB/チェックポイントの保守）。
変更可能なモジュール状態（`_cleanup_done`、`_OUTPUT_HISTORY`、
`_LIGHT_MODE_CACHE`、...）と `global` を書き込むすべての関数は `cli.py` に残ります。**Rich** はバナー/パネルを描画し、**prompt_toolkit**
は入力とオートコンプリートを処理し、`KawaiiSpinner`（`agent/display.py`）はAPI呼び出しをアニメーション表示し、
`┊` のアクティビティフィードを出力します。`load_cli_config()` は `cli.py` 内でCLIデフォルトとユーザーYAMLをマージします。

`hermes_cli/gateway.py` は `hermes gateway` ファサードです（プロセス探索、PM 対応 systemd ユニットの生成・更新、コマンドディスパッチ）。ファサードから再エクスポートされる同系統のモジュールには、`gateway_launchd.py`（macOS LaunchAgent バックエンド）、`gateway_setup_wizard.py`（`hermes gateway setup`: `_PLATFORMS` レジストリ、ステータステーブル、プラットフォーム別プロンプト、サービス提供）、`gateway_windows*.py`、`gateway_supervised_restart.py`、`gateway_migrate*.py`、`gateway_multiplex_*.py`、`gateway_enroll.py`、`gateway_command_errors.py` があります。`_resolved_launchd_domain` のような可変状態はファサードのグローバルとして保持されます。

`process_command()` は `resolve_command()` を介して正規名を解決し、`HermesCLI._SLASH_DISPATCH`（`canonical -> (method name, pass_arg)`）を通じてディスパッチし、命名規則により `_handle_<name>_command` メソッドにフォールバックします。**`elif` ラダーは存在しません — 追加しないでください。**

スキルのスラッシュコマンド（`agent/skill_commands.py`）は `~/.hermes/skills/` を走査し、**ユーザーメッセージ**として注入します。システムプロンプトには決して注入しません（プロンプトキャッシュのため）。

ルール: すべての対話型メニューピッカーは curses を使用します（`hermes_cli/curses_ui.py`; 例 `hermes_cli/tools_config.py`）。スピナーや表示コードで `\033[K`（ANSI の行末消去）を出力しないでください — prompt_toolkit の `patch_stdout` ではリテラルな `?[K` として漏れます。代わりにスペースでパディングしてください: `f"\r{line}{' ' * pad}"`。ラッパー CLI は `cli_tui_mixin.py`（`website/docs/developer-guide/extending-the-cli.md`）の保護フックを介して拡張し、`run()` をオーバーライドしないでください。

## スラッシュコマンドレジストリ（`hermes_cli/commands.py`）

`COMMAND_REGISTRY`（`CommandDef`のリスト）が唯一の情報源であり、そこからすべてが導き出されます。CLIディスパッチ（`resolve_command()`）、ゲートウェイの`GATEWAY_KNOWN_COMMANDS`＋ディスパッチ、`gateway_help_lines()`、`telegram_bot_commands()`（BotCommandメニュー）、`slack_subcommand_map()`、`COMMANDS`（オートコンプリート）、`COMMANDS_BY_CATEGORY`（`show_help()`）です。フィールド：`name`（スラッシュなし）、`description`、`category`（`Session | Configuration | Tools & Skills | Info | Exit`）、`aliases`タプル、`args_hint`、`cli_only`、`gateway_only`、`gateway_config_gate`（設定のドットパス。真と評価されると`cli_only`コマンドがゲートウェイで利用可能になります。`GATEWAY_KNOWN_COMMANDS`は常にゲート対象のコマンドを含むため、ゲートウェイはそれらをディスパッチできます。ヘルプ／メニューはゲートが開いているときだけそれらを表示します）。

**コマンドの追加：** (1) `CommandDef("mycommand", "What it does", "Session", aliases=("mc",),
args_hint="[arg]")` を `COMMAND_REGISTRY` に追加する。(2) 関連する `cli_*_mixin.py` に `_handle_mycommand_command(self, cmd_original)` を追加する（規約により自動的に認識される）。メソッド名や引数の渡し方が異なる場合は、明示的な `_SLASH_DISPATCH` エントリ `"mycommand": ("_handle_mycommand", True)` を追加する。(3) ゲートウェイについては、対応する `gateway/slash_commands_*.py` ミックスインに `_handle_mycommand_command(self, event)` を追加し、`gateway/run_busy.py` 内の `_IDLE_COMMANDS`（実行途中で動作させる必要がある場合は `_PLAIN_COMMANDS`）に列挙する。ハンドラは `_command_handler_table` 経由で名前によって解決される。(4) 永続設定は `cli.py` 内の `save_config_value()` で行う。**エイリアスの追加** = `aliases` に追加するだけで、すべてのサーフェスが自動的に更新される。システムプロンプトの状態を変更するコマンドは、既定では `--now` によるオプトイン付きの遅延無効化となる（ルートの不変条件）。

### 共有ゴールコマンド

`hermes_cli/goal_command.py::dispatch_goal_command` が `/goal` の解析とマネージャの変更を管理する。CLI、メッセージングゲートウェイ、TUI/デスクトップ/ダッシュボード、およびデスクトップのゴールコントロールはすべてそこに委譲する。アダプタはセッションの解決、ゴール作成の承認、結果のレンダリング、キックオフ/継続プロンプトのスケジュールのみを行う。非同期呼び出し元は、ディスパッチをループ外で実行する際に ContextVars を保持する（ドラフト作成ではプロファイルスコープの補助資格情報を使用する）。サーフェス固有のゴールパーサを追加してはならない。ACP にはゴールコマンドもゴールループもまだ存在しない。

## 設定システム（`hermes_cli/config.py`）

- **config.yaml オプション:** `DEFAULT_CONFIG` に追加する。`_config_version` を上げるのは、既存の設定を能動的に移行・変換する場合（キーのリネーム、構造の再編成）のみ。新しいキーはディープマージで自動的に取り込まれる。トップレベルのセクション（網羅的ではない）: `model, agent, terminal, compression, display, stt, tts,
memory, security, delegation, smart_model_routing, checkpoints, auxiliary, curator, skills,
gateway, logging, cron, profiles, plugins`。`auxiliary` はタスクごとのサイドLLM上書き設定（`agent/AGENTS.md`）。`curator` は `enabled, interval_hours, min_idle_hours, stale_after_days,
archive_after_days, backup.*`。
- **.env はシークレット専用**（キー、トークン、パスワード）: `OPTIONAL_ENV_VARS` に `{"description", "prompt", "url", "password": True, "category": provider|tool|messaging|setting}` を付けて追加する。シークレット以外の設定は config.yaml に置く。内部コードが環境変数ミラーを必要とする場合は、コード内でブリッジする（`gateway_timeout`。`terminal.cwd` → `TERMINAL_CWD`）。`MESSAGING_CWD` は削除され、`.env` 内の `TERMINAL_CWD` は非推奨 — ローダーが警告を出す。正規の場所は `terminal.cwd`。`hermes config
set/get/unset <NAME>` は、`OPTIONAL_ENV_VARS` / `_EXTRA_ENV_KEYS` に登録された（または `setup_hidden_env` プラットフォーム接尾辞を持つ）任意のベア名を、プラットフォームセットアップフローが書き込むファイルである `.env` へ `config_env_routing.py` 経由でルーティングする — config.yaml のトップレベルには決して置かない。
- **単一の書き込みシーム。** `config.yaml`（メインまたはプロファイル）への書き込みはすべて、`hermes_cli.config.atomic_config_write`（省略による削除を拒否）または明示的な`atomic_config_replace`フルステートパス（→ `utils.atomic_roundtrip_yaml_save`、ruamelラウンドトリップ）を経由します。これによりフォーマットが保持され、フェイルクローズの読み取り不能ファイルガードが最初に実行されます。意図的な`pop()`／未設定／移行パスは`atomic_config_replace`を使用し、追加型の書き込みは`atomic_config_write`に留まります。設定パスに対して`atomic_yaml_write`／`yaml.dump`／`yaml.safe_dump`を呼び出さないでください。`scripts/check_config_yaml_writers.py`（CI lint）がこれを拒否し、`tests/hermes_cli/test_config_yaml_comment_preservation.py`が各パスをガードします（#92554）。コメント付きの例ブロックは、ファイルが作成されたときのみ追加されます。
- **読み取り**も`config_backend.py`のみを経由します。`developer-guide/config-backend.md`を参照してください。デーモン、RPC、ティックコードでは`ConfigBackendUnavailable`を明示的にキャッチします。これは`SystemExit`であるため、`except Exception`では停止しません。
- **3つのローダー — 自分がどれを使っているか把握せよ:** `load_cli_config()`（CLI、`cli.py`）; `load_config()`
  （`hermes tools/setup`、ほとんどのサブコマンド、`hermes_cli/config.py`、`DEFAULT_CONFIG`をマージ）;
  `hermes_cli/config_effective.py::load_user_config_effective()`（`gateway/run.py::_load_gateway_config`経由のゲートウェイランタイム、TUIゲートウェイ`_load_cfg`、cron、`hermes send`、doctor、
  `hermes_time`/`hermes_logging`: ユーザーファイル + 管理オーバーレイ + `${VAR}`展開 + モデルキー
  正規化、デフォルトなし — 存在に敏感な読み手向け）。CLIがキーを認識するのにゲートウェイが
  認識しない（またはその逆）なら、ローダーを間違えている — `DEFAULT_CONFIG`のカバレッジを確認せよ。
  raw-read → overlay → expand を手書きするな。`read_user_config_raw`は書き戻しの往復専用である。
- **すべての`DEFAULT_CONFIG`キーにはランタイムリーダーがあり、すべてのリーダーにはレジストリエントリがある。** 両方の
  ドリフトモードは無音である: 登録されているのに誰も読まないキー（何もしないノブ）と、
  一度も登録されていないキーのリーダー（表示されず、移行もされない。新しいルートも`_KNOWN_ROOT_KEYS`に入れる）。
  新しいキーには: `search_files`を`"<key>"`用に`hermes_cli/config_defaults.py`で、かつ`<key>`用に`tests/`の外側で
  両方にヒットさせ、1つの不変条件テストが一時`config.yaml`でそれを設定し、消費側サーフェスが使うローダーを
  通じて挙動を検証する。マルチプレックス下ではプロセス環境はプロファイルのYAMLを上書きしない。
- **作業ディレクトリ:** CLIは`os.getcwd()`を使い、メッセージングは`terminal.cwd`を使い、子ツール用に
  `TERMINAL_CWD`へブリッジされる。

## スキンエンジン（`hermes_cli/skin_engine.py`）

スキンは**純粋なデータ**（`SkinConfig`）です。追加するのにコード変更は不要です。`init_skin_from_config()`は起動時に`display.skin`を読み込みます。`get_active_skin()`（キャッシュ済み）、`set_active_skin(name)`（`/skin`）、`load_skin(name)`（ユーザー`~/.hermes/skins/*.yaml` → 組み込み → デフォルト。欠落した値は`default`から継承）。`_BUILTIN_SKINS`内の組み込み：`default`、`ares`、`mono`、`slate`。キー：`colors.*`（バナーの枠線・タイトル・アクセント・ディム・テキスト、response_border）、`spinner.*`（待機中・思考中のフェイス、thinking_verbs、wings）、`tool_prefix`、`tool_emojis`、`branding.*`（agent_name、welcome、response_label、prompt_symbol）。利用者：`banner.py`、`display.py`、`cli.py`。キーごとの表とYAMLテンプレート：`website/docs/user-guide/features/skins.md`。

## 更新パイプライン（`hermes update`）

トランザクション型で、`plan → snapshot → apply → restart-per-kind → verify → report`。各ステージは実際のフィールド障害を保護します（フリートキャンペーン #91277）。ステージを弱めるPRは、そのクラスに対して責任を負います。ステージごとの契約：`website/docs/developer-guide/cli-internals.md` § 更新パイプライン。

- スナップショットは、すべてのプロファイルを同一のファイルセット1つでカバーします（部分適用や段階適用はありません）。ファイル消失からの復旧を担い、ロールバックは`--backup`が所有します。
- WindowsのZIPフォールバックは、git自体が失敗した場合にのみ発動し、ダーティなツリーを拒否し、`_ZIP_PRESERVED_NESTED`のビルド成果物をスワップに接ぎ込みます。
- 再起動はフリート全体で、ドレイン優先です。各ユニットが動作するホームを上限とし（`update_fleet_scope.py`）、別のインストールのランタイムを再起動することはありません。
- コミット後の失敗はフォローアップの対象となり、終了コードは0です（stashは1、Ctrl-Cは130）。領収書はROOTの`logs/update_receipts/`にあります。
- 取得済みコードを事前取得インタープリタで実行することはありません。`update_handoff.py`と`update_serve_obligations.py`はFROZEN互換サーフェスです（`tests/compat/old_updater_surface.json`）。名前を削除すると、更新途中のリリースが壊れます。
- プロセススキャンのヒューリスティックを追加する前に、#92091（ゲートウェイ所有の制御ソケット）を読んでください。

## プロファイル（マルチインスタンス）

`_apply_profile_override()` は `hermes_cli/main.py` 内で、単一プロファイル向けコマンド（`hermes -p x <cmd>`）のモジュール import より前に `HERMES_HOME` を設定するため、そこでは `get_hermes_home()` はアクティブなプロファイルにスコープされます。一方、マルチプレックスゲートウェイと Desktop/ダッシュボードの `serve` バックエンドは、contextvar によるオーバーライドでアクティブなプロファイルをアクティビティごとにバインドし、`os.environ["HERMES_HOME"]` は起動プロファイルを保持します。そのため、そこでモジュール定数や import 時読み取りを行うと起動プロファイルに固定されます（ルールは root にあります）。プロファイルは設計上、独立した島です。ライブでの設定継承はありません。`--clone` は作成時にコピーしますが、メッセージングチャネルは除きます（`profile_channels.py`: 所有権ベースのインベントリは SOURCE のプラグインスコープで評価されます。アダプターが宣言したキー + 正規/エイリアス接頭辞 + `GATEWAY_ALLOW*`/`GATEWAY_RELAY_*`。ツールと共有される接頭辞（`TWILIO_`/`EMAIL_`、およびプラグインプラットフォームの `shared_env_prefixes`）は、そのソースが当該アダプターを実行している場合にのみ除去されます。手動リストは決して使いません。コアを離れたプラットフォームは、プラグインが存在しない間も自身の `LEFT_CORE` 行から所有権を保持します）。`--clone-channels` はオプトインし、そのライブマルチプレクサー拒否は `create_profile` にあります（CLI、REST、TUI はすべてそこを通ります）。クローンは `profiles/.<name>.staging-<pid>` で構築され（隠し → `_iter_named_profile_dirs` とホットサーブ再スキャンには不可視）、ストリップ後に単一の `os.rename` によって公開されます。シンボリックリンクされた `.env`/`config.yaml` は最初に実体化されるため、クローンがソースに書き込むことはありません。マルチプレックス（`gateway.multiplex_profiles`）のシークレットスコープ規則: `gateway/AGENTS.md`。提供されるセットは `profiles.py::profiles_to_serve(multiplex=True)` = デフォルト + `profiles/` 配下のすべてのライブディレクトリです。ライブとは、アイデンティティマーカー（`hermes_constants.named_profile_has_identity`: `config.yaml`/`.env`/`SOUL.md`/`profile.yaml`/`auth.json`/`state.db`）を持ち、トゥームストーン化されていないことを指します。マーカーのないディレクトリ（cron/ログの副作用シェル、迷子のインフラディレクトリ）は、一覧表示、提供、ティック、`.env` バックフィル、`-p` 経由での解決を一切行いません（#95188、#99392）。`profile create` は、それが同時にトゥームストーン化されている場合にのみ置き換えます（ライブのマーカーなしディレクトリはユーザーファイルを保持している可能性があります。フェイルクローズし、rmtree は決して行いません）。ぶら下がったシンボリックリンクのマーカーもアイデンティティとして数えます（`is_symlink()`）。`tools/bot_mode_probe._roster`（Bot Mode のチームメイト名簿、`bot_relay.deliver` のターゲットチェック）も同じ述語を適用します。許可リストはありません（`gateway.multiplex_profile_allowlist` は設定 v43 で廃止されました）。列挙は純粋な読み取りです。提供されたパスからプロファイルホームを `mkdir` することは決してありません（セッションストア、ロギング、cron はすべて `mkdir_under_hermes_home` / `_ensure_cron_dir` を通り、これらは削除または欠落した名前付きプロファイルを拒否します、#94590）。プロセスグローバルなプロファイルごとのスロット（`mcp_startup.py` での MCP ディスカバリ、ツールレジストリのオーバーレイ）は、単一のフラグではなく `hermes_constants.hermes_home_key()` をキーにします。`gateway.multiplex_profiles` はデフォルトで **オン** ですが、`GatewayConfig` は未設定フラグを `None` のままにし、`gateway_multiplex_mode.resolve_multiplex_mode` がブートごとに一度だけそれを確定します（`load_gateway_config_for_runner` から呼び出されます）: デフォルトプロファイル、2 つ以上のプロファイル、スタンドアロンのセカンダリゲートウェイなし、プリフライトブロッカーなし、移行可能なホスト → `True`。それ以外は `False` + 記録された理由。明示的な値はそのまま通します。CLI/ダッシュボードの読み取り側は `default_gateway_multiplexes`（ライブの `served_profiles` レコード、次に明示的なフラグ）を使用します。マージされたデフォルトは決して使いません。それはゲートウェイだけが下す判定を推測することになるからです。プロファイル別ゲートウェイからの移行: `hermes_cli/gateway_migrate.py`（`hermes gateway migrate
--multiplex`、唯一のモード — `--standalone` は削除され、プロファイル別フリートはサポート対象外です。テーブル駆動の `_PREFLIGHT_CHECKS`。マニフェスト `<default>/gateway_migration.json` = UNFINISHED、再実行はそこから再開します。名前付きプロファイルの `gateway install|start|run` は、`--force` なしでは `gateway.py::_named_profile_refused_under_multiplexer` 経由で拒否します。ダッシュボードの双子は `web_server_gateway.py::multiplexed_profile_refusal`）。`update_cmd_fleet_verify._verify_fleet_after_update` は成功パスでのみ `maybe_auto_migrate_after_update` を呼び出します。`gateway_migrate_guards.py` は自動パスのみの拒否を保持します（テーブル `_AUTO_MIGRATION_GUARDS`: 他のサービスドメイン / UNIX ユーザー / `profiles/` 外の HERMES_HOME — 明示コマンドには通知、フックにはブロッカー）と `gateway.auto_multiplex_migration` のオプトアウト（#109954）。ブロッカーは `GatewayRunner._adapter_credential_fingerprint` と `platform_binds_port` を再利用します。「`/p/<profile>/` イングレスを持つ」はアダプタークラス属性 `serves_profile_prefix` です。新しい HTTP 受信アダプターがその接頭辞に応答する場合は、それに設定してください。ここでリストを拡張しないでください。Hermes がインストールしていないゲートウェイ向けの `hermes gateway restart`（カスタム launchd エージェント / `gateway run --external-supervisor` を実行するユニット）: `gateway_supervised_restart.py` — ゲートウェイ自身が宣言したスーパーバイザー（制御ソケット `identify` が `manual` 以外に応答する、または argv マーカー）が決定します。SIGUSR1 で返し、新しい監視対象 PID を待ちます。停止してフォアグラウンドで `run_gateway` することは決してしないでください（それは CLI の PID を刻印し、すべての KeepAlive 再スポーンを詰まらせます、#110637）。

サービスインストールはユニットファイルではなくマトリクスです。`gateway.py::generate_systemd_unit(system=,
run_as_user=)`（systemdユニット生成 / `systemd_unit_is_current` / `refresh_systemd_unit_if_needed` はPM対応ファサードのオーナー。ユーザーユニットと `--system` ユニットを `User=` で扱う。解決不能な `User=` はブロッカーであり、ディレクトリオーナーへのフォールバックではない）、`gateway_launchd.py::generate_launchd_plist`（`gui/<uid>` の後に `user/<uid>` ドメイン。`~/Library/LaunchAgents` グロブは不可。launchdバックエンド全体 — plistの再読み込み、`launchctl` のbootstrap/kickstart、`launchd_start/stop/restart/status`、デタッチプロセスへの縮退 — はその兄弟に存在し、ドメインキャッシュ `_resolved_launchd_domain` はファサードのグローバルに留まる）、Windowsのスケジュールタスク、およびデスクトップ起動バックエンドはすべて、プロファイルの `HERMES_HOME`（サービスユーザーには `HOME` も）を明示的に保持します。スーパーバイザーは空の環境で起動するため、`-p` を対話的に機能させる環境上書きはそこには存在しません。インストール/再起動/ステータスの変更はすべての種類を再生成して差分を取ります。ユーザーユニットとシステムユニットの両方が存在する場合は両方記録されます。プロセスの生存確認は `(pid, start_time)` または正規のマッチャー（`gateway.status.live_gateway_pid_for_home`）であり、素のPID存在チェックではありません。

## Nous無料枠（`hermes_cli/anon_auth.py`）

`anon_auth.run_sign_in()` は唯一のサインイン構成であり、それ自体の `SignInState` を生成し、それらは独自の `.copy` / `.copy_terminal` を保持し、完了したプロモーションとトークン付与の両方が行われた後でのみ永続化され、完了ごとに `settle_after_upgrade` をちょうど一度だけ実行します。`hermes auth upgrade`、CLI とゲートウェイの `/login`、そしてデスクトップのポーラーは、いずれもその上に構築されたレンダラーです。デスクトップのプレーンなデバイスコードログイン（`_nous_plain_poller`）は、別個のパスとして残ります。詳細は `cli-internals.md` § Nous 無料枠サインインを参照してください。
