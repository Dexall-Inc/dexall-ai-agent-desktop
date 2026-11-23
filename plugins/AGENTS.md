# plugins/ — プラグイン種別、互換性契約、ツリー内ポリシー

ルートの `AGENTS.md` に重ねて適用されます。オーサリングガイドと標準の互換性契約:
`website/docs/developer-guide/plugins/index.md`。種別ごとのガイド: `memory-provider-plugin.md`、
`model-provider-plugin.md`、`context-engine-plugin.md`、`image-gen-provider-plugin.md`、...

## プラグインはコアに触れない (Teknium、2026年5月)

プラグインは専用ディレクトリに置かれ、私たちが提供する ABC / フック / `ctx` のサーフェス内で動作します。
プラグインは `run_agent.py`、`cli.py`、`gateway/run.py`、`hermes_cli/main.py` などを変更してはなりません (MUST NOT)。
フレームワークに欠けている機能が必要な場合は、**汎用**のプラグインサーフェスを広げ (新しいフック、新しい
ctx メソッド)、プラグインにそれを使わせてください — プラグイン固有のロジックをコアにハードコードしないでください (PR #5295
は `main.py` からハードコードされた honcho argparse 95行を削除しました)。プラグインのセットアップは
`hermes memory setup` → `provider.post_setup(hermes_home, config)` を通じて行い、並列のトップレベル
コマンドは決して作らないでください。具体的な消費者を持たないフックは投機的なインフラであり、拒否されます (ルート)。

## このツリーに置いてよいもの (ポリシー)

- **新規のツリー内メモリプロバイダーは追加しない（2026年5月）。** `plugins/memory/` はクローズされました（byterover と retaindb は 2026年10月15日の削除まで残ります）。hindsight（2026年9月）、honcho、supermemory、mem0、openviking、holographic（2026年10月）はプラグインカタログに移動しました — `plugin-catalog/<name>.yaml` で、それらに設定済みのホームには `hermes_cli/memory_provider_migration.py` が自動インストールします。コアはこれらのためのプロバイダー固有コードを保持しません。プロバイダーは `MemoryProvider.on_profile_created` / `on_profile_renamed` を通じて自らのプロファイル設定を、`storage=STORAGE_PROVIDER` + `read_config_fields` / `write_config_fields` を通じて自らのダッシュボード設定ファイルを所有します。依然としてプロバイダーモジュールを必要とするホスト側コードは、`plugins.memory.import_provider_module` を通じて解決し、`plugins.memory.<name>` インポートは決して使用しません。新しいバックエンドは、同じ `MemoryProvider` ABC を実装するスタンドアロンリポジトリとして提供され、同じパスを通じて発見され、`hermes memory setup` / `post_setup()` を通じて統合されます。
- **コアから外れるその他の機能**（Home Assistant プラットフォーム＋ツールセット、2026年10月→
  `plugin-catalog/homeassistant.yaml`。Spotifyツールセット→`plugin-catalog/spotify.yaml`。Singularity
  ターミナルバックエンド→`plugin-catalog/singularity.yaml`）は、名前・設定・環境変数を維持したまま、
  `hermes_cli/left_core_migration.py::LEFT_CORE`（カタログプラグイン＋読み取り専用の「このホームが使用中」述語）に行を追加します。
  `hermes update`とエージェント／ゲートウェイの起動時に、使用していたホーム向けにプラグインをインストールします。
  インストールとコア時代の状態の変換は別の手順です。ツールセット単位の変換は、プラグインが既に存在する場合でも、
  ホームと行ごとに1回実行されます（config.yaml内の`_left_core_scoped`）。
  自動インストールもホームと行ごとに1回実行されます（`_left_core_installed`。プラグインディレクトリが存在した場合のみ書き込まれます）。
  後からの`hermes plugins remove`は維持され、失敗したインストールは再試行されます。
  コアの特殊ケースは、プラグインが設定する`PlatformEntry`シームになります（`trusted_inbound`、
  `display_tier`、`shared_env_prefixes`）。名前チェックにはなりません。
  コアの`hermes auth <name>`ログインは、プラグイン独自の`hermes <name>`コマンドになります（行フィールド`cli`。古い表記は新しいものを表示します）。
  ネストされたコアコマンドはトップレベルのプラグインコマンドになります（`command`＋`old_command`：
  `hermes mcp serve`→`hermes mcp-serve`）。
  ホーム内シグナルのない機能（MCPクライアントはHermesの外に存在）には、常にFalseの`in_use`が付きます。
  ヒントのみで、自動インストールは行いません。
  組み込みターミナルバックエンドは、プラグインが登録できるように`BUILTIN_BACKEND_NAMES`から名前を外します
  （行フィールド`terminal_backend`。不明なバックエンドのエラーはインストールコマンドを名指しします）。
  コアから外れるモデルプロバイダー（GitHub Copilot→`github-copilot`）は、そのIDとエイリアスを列挙します
  （`providers`。不明なプロバイダーのエラーはインストールを名指しし、実行時の解決は使用中のホームに対して最初にインストールし、
  models.devが代役になることはありません）。コアがプロファイル管理していた環境変数（`profile_env`）、
  全ホームで環境変数ライターが拒否する実行ファイル／argvサブセット（`launch_env`）、
  コアが任意のプロバイダー名に対してホストが提供していたホスト群（`hosts`。そこへのルートは使用を意味し、
  そこで拒否されたリクエストはインストールを名指しします）。
  `notice`は、すべての結果にホームごとの文を追加します（プラグインがもう読み取らない資格情報ソース）。
- **新規のサードパーティ製プラグインは追加しない（2026年6月）。** オブザーバビリティ／メトリクスバックエンド、ベンダー製SaaSコネクタ、分析ダッシュボード、有料サービス連携は、独立したプラグインリポジトリ（`~/.hermes/plugins/`またはpipエントリポイント）として提供し、Discord `#plugins-skills-and-skins`で宣伝する。理由：取り込んだ製品はすべて、我々が所有していないバックエンドに対して、急速に進化するコアを維持しながら抱える保守負担となるからだ。`kanban/`、`disk-cleanup/`は前例であって招待ではない（Langfuseはすでに公式カタログプラグインへ移管済み）。そのようなPRをクローズすることは、品質評価ではなく結合判断である。
- リファレンス／ドキュメント併設プラグイン（`example-dashboard`、`strike-freedom-cockpit`、`plugin-llm-example`、`plugin-llm-async-example`）は[`hermes-example-plugins`](https://github.com/NousResearch/hermes-example-plugins)に置かれ、ここには置かない。

## プラグインカタログ（`plugin-catalog/`、2026年9月）

アウトオブツリー（ツリー外）プラグインの唯一の検出システム。エントリごとに1つのYAML、40桁16進数のSHAピン留めが必須。PR経由で人間がマージする（`plugin-catalog/README.md`＝受け入れポリシー。提出ガイドとともに`website/docs/developer-guide/plugins/catalog-submission.md`に逐語でミラーされる。`plugin-catalog-ci.yml`は変更された各エントリをそのピンでクローンし、`hermes plugins validate`を実行する）。`removed.yaml`はキルリストであり、すべてのインストール経路（CLI、ダッシュボード、TUI）が一致を拒否する（リポジトリURLは正規化された`host/owner/repo`で比較されるため、`git@`／`ssh://`／`www.`の表記は一致する）。CLIのみが明示的な`--allow-removed`を持ち、これはインストールレコードに記録され、インストール済みプラグインが`update`、`enable`およびロード時（`gate_manifest`）の同じチェックを免除される唯一のものである。カタログの出所は、インストーラーが所有する`.install-metadata.json`レコード（`catalog`ブロック、sha＝チェックアウトされたコミット）にあり、決してツリー内にはない。ツリー内の`.hermes-catalog.json`は、デスクトップが「ここにインストール」のために読み取る便宜上のコピーであり、Pythonはこれを決して信頼しない（リポジトリが偽造品を同梱できるため）。

コード：`hermes_cli/plugin_catalog.py`（ローダー。ドキュメントビルドが公開する`/docs/api/plugin-catalog.json`からのライブリフレッシュ、ツリー内フォールバック）、`hermes_cli/plugins_cmd_catalog.py`（解決、`.hermes-catalog.json`の出所サイドカー、検索／情報／検証、`update`での再ピン留め、ダッシュボード／TUIペイロード）。2つ目の名前インデックスを追加しないこと。素の名前はカタログ経由で解決するか、エラーになる。

## プラグインの種類とその検出システム

| 種類 | 場所 | 検出方法 | 備考 |
|---|---|---|---|
| 一般 | `plugins/<name>/`、`~/.hermes/plugins/`、`./.hermes/plugins/`、pip エントリポイント | `PluginManager`（`hermes_cli/plugins.py`）、後勝ち | `register(ctx)` がフック（`pre_tool_call`、`post_tool_call`、`pre_llm_call`、`post_llm_call`、`on_session_start`、`on_session_end`）、ツール（`ctx.register_tool`）、CLI サブコマンド（`ctx.register_cli_command` — 起動時に `hermes` へ配線される argparse ツリーで、`main.py` の変更は不要）、言語パック（マニフェスト内の `provides_locales` が `ctx.register_locale_dir` 経由で `locales/<lang>[.tui|.desktop].yaml` を自動登録。マニフェストのみのパックは `__init__.py` が不要。`hermes_cli/plugin_validate_locales.py` が検証する）を登録する |
| メモリプロバイダ | `plugins/memory/<name>/` | `plugins/memory/__init__.py`：同梱 → `$HERMES_HOME/plugins/` → `./.hermes/plugins/`（オプトインの `HERMES_ENABLE_PROJECT_PLUGINS`）→ `hermes_agent.memory_providers` エントリポイント。**同梱優先** | `memory.provider` 経由で名前を指定して有効化するため、追加配置したディレクトリが出荷済みのものを覆い隠してはならない（一般の後勝ちとは逆）。インポートせずに列挙する。`MemoryProvider` ABC（`agent/memory_provider.py`）を実装し、`agent/memory_manager.py` が統括する：`sync_turn`、`prefetch`、`shutdown`、任意の `post_setup`。`register_cli(subparser)` を伴う `cli.py` は `discover_plugin_cli_commands()` によって配線される — アクティブなプロバイダのみを対象とするため、`hermes --help` はクリーンなまま保たれる |
| モデルプロバイダー | `plugins/model-providers/<name>/` | `providers/__init__.py._discover_providers()`、**遅延**、最初の`get_provider_profile()`/`list_providers()`時。バンドル済み → `$HERMES_HOME/plugins/model-providers/` → レガシー`providers/<name>.py` | `__init__.py`は読み込み時に`providers.register_provider(ProviderProfile(...))`を呼び出す。**最後に書いた者が勝つ**ため、ユーザープラグインがバンドル済みプロファイルを上書きする。`PluginManager`は`kind: model-provider`のマニフェストを記録するが、インポートはしない（二重インスタンス化になるため）。`kind:`のないマニフェストは、ソースのヒューリスティック（`register_provider` + `ProviderProfile`）で自動的に強制変換される |
| コンテキストエンジン / 画像生成 / 委譲 / その他 | `plugins/context_engine/`、`plugins/image_gen/`、`plugins/delegation/`、... | ABC + オーケストレーター + プラグインごとのディレクトリ | `agent/context_engine.py`、`agent/image_gen_provider.py`、`agent/delegation_provider.py`に接続する（`plugins/delegation/default`が今日の委譲ルーティング） |
| プラットフォームアダプター | `plugins/platforms/<name>/adapter.py` | ゲートウェイ | `gateway/AGENTS.md`のトークンロックとスコープ付きシークレットのルール（`irc`、`feishu`が正規） |

**ディスカバリのタイミングに関する落とし穴:** `discover_plugins()` は `model_tools.py` をインポートした副作用としてのみ実行されます。`model_tools.py` を先にインポートせずにプラグインの状態を読み取るコードは、`discover_plugins()` を明示的に呼び出す必要があります（冪等）。フックは `model_tools.py`（ツールの前後）と `run_agent.py`（ライフサイクル）から呼び出されます。強制されない `discover_plugins()` は `_discovered` で短絡します。実行途中のあらゆるロード経路（任意のサーフェスでのインストール/有効化/更新、`reload-plugins` 動詞）は `discover_plugins(force=True)` を実行し、`PluginManager.on_plugin_loaded` はそのスイープの内部から、新しくロードされたプラグインに対してアクティベーションのサマリー付きで発火します（`hermes_cli/plugins_activation.py`: ハンドラーは即時有効、ツール/プロンプトは次セッション、`deferred.mcp_servers` は `mcp.reload` まで）。そのイベントを RPC から発行してはなりません。補助的な LLM 呼び出し（タイトル付け、圧縮、MoA、ビジョンなど）は `agent/auxiliary_hooks.py` から `pre_auxiliary_call`/`post_auxiliary_call` を発火します（ペイロードは `*_api_request` の形状 + `aux_task`）。これらがターンスコープの `pre/post_api_request` を発火することはありません（#79733）。プラグインがデフォルトを変更する場合は、「既存の設定」シグナル（`_explicitly_configured`）をキーにした移行ガードを追加し、既存ユーザーが古いデフォルトを維持できるようにしてください。

**ライフサイクルフックは所有プロファイルのスコープ下で発火し、呼び出し側がそれをバインドします。**
`on_session_start`/`on_session_end`/`sync_turn`/`shutdown` は、ターン（バインド済み）から、および eviction、シャットダウン、`tui_gateway` のティアダウン、cron 完了時（呼び出し側が `_run_release_in_profile_scope`、`_session_profile_runtime_scope`、`_profile_cron_scope` 経由でバインド）から呼び出されます。1つのプロセスが複数のプロファイルにサービスを提供するため、プロバイダーは `hermes_home` を `initialize()` から「その」ホームとしてキャッシュすることはありません。呼び出しごとに渡されるホーム（`hermes_home_key()`）で状態をキー付けし、資格情報のために `os.environ` を読み取ることは決してありません（`agent.secret_scope.get_secret`。`check_fn` も同様）。バックグラウンド処理は `agent.memory_provider.spawn_context_thread` 経由で開始し、素の `threading.Thread` は決して使わないでください。さもないとワーカーがスコープなしで実行され、フェイルクローズするか（または起動プロファイルのテナントに書き込んでしまいます）。プラットフォームプラグインは `os.environ` を変更しません。YAML は `_shared.apply_yaml_bridge` 経由で `PlatformConfig.extra` に渡され、ゲートは `platform_gate_env`（`gateway/AGENTS.md`）経由です。

## プラグインホスト境界（`plugins.isolation: host`）

`in_process`（デフォルト）はユーザープラグインを Hermes にインポートします。`host` はバンドルされていないすべてのプラグインを、プロファイルごとのホストプロセスで実行します（`hermes_cli/plugin_host.py` が親側、`plugin_host_child.py` が子、`plugin_host_wire.py` がフレーム化された JSON プロトコル）。子はプラグインに `RemotePluginContext` を渡し、Hermes はプロキシ（ツール、フック、コマンド、およびそれがチェックする ABC のサブクラスとしてのプロバイダーオブジェクト）を登録します。

不変条件:

- **すべてのユーザーコードのインポートパスはホストにルーティングされるか拒否される** — 汎用プラグイン（`plugins_loader`）、メモリ／コンテキストエンジン／cronプロバイダー（`load_instance`）、モデルプロバイダーのプロファイル（`plugin_host_profiles.py`：ファイルフィンガープリントでキャッシュされる資格情報なし抽出。`hermes_cli.config`／`auth`のインポート中にディスカバリが実行されるため。オーバーライドはホスト内で名前によって実行される）、ダッシュボードAPI（ASGIブリッジ）。`plugins/plugin_loader.load_plugin_module`はその他の合成名前空間インポートを拒否する。新しいユーザーコードローダーも同じことを行わなければならない。
- **越境できないのは1つのテーブルだけ**：`plugin_isolation.HOST_UNSUPPORTED_CTX_METHODS`（ライブゲートウェイ／アダプタオブジェクト）。実行時の拒否と静的監査（`plugin_isolation_audit.py`、`hermes plugins validate/show`で表示される）の両方がこれを読み取る。`evals/plugin_isolation/audit_catalog.py`がカタログを再測定する。
- **値はプロバイダーABCの宣言された型をワイヤー越しに維持する**：JSONはdict、リスト、スカラーを運ぶため、`plugin_host_wire.restore`はABCのアノテーション（`FetchResult`、`Path`、enum、プロキシとして返されるエンジン）から引数（子）と結果（親）を再構築する。コアコンシューマーが型チェックする値は、ABCメソッドでアノテーションされたdataclassでなければならない。さもなければ`Record`／`Opaque`として届く。
- **ホストはホストを生成しない**（`HERMES_PLUGIN_HOST_PROCESS=1`がそこで`isolation_mode()`をインプロセスにする）し、モジュールインポートがそのロックを保持している間は起動してはならない（モデルプロバイダーのディスカバリが既知のケース）。
- **隔離された当事者は、オペレーターがそれを固定した場合にオプトアウトできない**：`isolation_mode()`／`host_launcher()`は管理オーバーレイ（`load_config_readonly`）を通じて読み取るため、`/etc/hermes/config.yaml`はプロファイル自身の設定に勝る。これらを生のユーザー設定読み取りに切り替えてはならない。
- プラグインはテナント非認識のまま：新しいAPIなし、同じ`ctx`。プロファイルごとのenvは`served_profile_child_env`から来るため、ホストは自分のプロファイルのシークレットだけを見る。

## ネイティブプラグイン互換性契約（要約 — 正規のテキストはドキュメントページにあります）

互換性は**振る舞いの契約**であり、一枚岩の`PLUGIN_API_VERSION`、マニフェスト全体にわたるネイティブ`api:`の一致、または無関係なペイロード上のバージョンリテラルではありません。文書化されたサーフェスは追加的であり続けます：

- フックペイロードデータは**キーワードフィールド**として追加されます。コールバックはシグネチャ検査されるため、古い狭いシグネチャは宣言したフィールドのみを受け取り、`**kwargs`コールバックは完全なペイロードを受け取ります。
- `PluginContext`メソッドを削除または名前変更しないでください。新しいパラメータはデフォルト値付きのオプションとし、可能な場合はキーワード専用にします。
- 未知のネイティブマニフェストフィールドは無視されます。
- 新しいプロバイダーメソッドにはデフォルト実装が提供されます。オプションのコールバックkwargsはシグネチャ検査され、無条件に転送されることはありません。
- ローカルスキーマバージョンは、ワイヤまたは永続化された契約を持つ機能に対してのみ存在し、古い状態/設定/セッションのリプレイは保持または移行されます。
- 非推奨化：プロセスごとに一度の警告、文書化された置き換えと移行ノート、削除前に2回以上の後続マイナーリリース。
- 互換性テストは**実際のディスカバリーパスを通じて凍結プラグインを読み込み**、結果を検証します。正確なレジストリ/カタログ数、ソース読み取りテスト、または「グローバルバージョンリテラルが変更された」ことは決して行いません。

## 境界リント（`scripts/boundary_lint.py`）

CIは、バンドルされたプラグインが`hermes_cli/data/plugin_api.json`にないコアの名前をインポートした場合、またはコアが特定のバンドル済みプラグインをインポートした場合に、コミット済みベースラインが記録しているよりも頻繁に失敗します。すでにそのリストにある名前、`ctx`メソッド、またはディスカバリで修正してください。リストに該当するものが何もない場合は、まずそのシームを独自のPRで追加し、それを必要とするプラグインを指定してください。`ctx`メソッドまたはフックを優先し、それ以外の場合は`plugin_api.json`（`module:Name`）に名前をリストし、`scripts/gen_plugin_api_docs.py`で`public-api.md`を再生成し、文書化して動作テストを追加してください。リストされた名前はすべてのプラグイン作成者に公開されます。lintを通すためだけにリストしないでください。

`--update`はツリー全体からベースライン全体を書き換えるため、その差分に意図した行だけが含まれていることを確認してください。意図したクロッシングのために実行し（PR本文にその理由を記載）、別のファイルに移動したインポートのため（ベースラインはインポート元ファイルごとにカウントされます）、またはクロッシングを削除した後に実行して、より低いカウントが維持されるようにしてください。CIを緑にするためだけに実行しないでください。

カタログプラグインには反対側から同じルールが適用されます。`scripts/ci/catalog_core_imports.py check`（Repository guards）は、コアのPRが固定されたカタログプラグインがインポートするモジュールまたは名前を削除した場合に、警告を発しますが、失敗はしません。コアの名前、それがプライベートかどうか、および各プラグインのカタログエントリ、リポジトリ、行を指定します。

## 内部インポートパスはAPIではありません

PR #102117 は内部実装を `<stem>_<topic>` の兄弟要素へ移動しました。旧 import パスを外部プラグイン向けに維持していた一時的な互換レイヤーは、2026-09-14 の期限を過ぎたため削除されました。旧パスは現在 `ImportError` を送出し、`hermes plugins list` ではプラグインのロードエラーとして表示されます。プラグインは `ctx` と文書化された ABC の上に構築してください。内部移動のために re-export のシムを追加しないでください。唯一の例外は、ピン留めされたカタログプラグインが import する、一覧にあるターンヘルパーです（プラグインガイド § ピン留めされたカタログプラグイン向けに維持されるターンヘルパー。v0.27.0 で `hermes_state` の代替とともに削除）。`hermes_cli/plugin_compat.py` は、削除前のアップデータが import する、3 つの不活性スタブとしてのみ残っています。

## テスト

`tests/plugins/`。一時的な `HERMES_HOME` を使った実際のディスカバリ経由でロードし、カウントではなく挙動（ツールが登録される、フックが期待どおりの kwargs で発火する）を検証してください。オプトインのテレメトリルールはプラグインにも適用されます。帰属タグはデフォルトでは付属しません。
