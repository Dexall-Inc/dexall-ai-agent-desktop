# gateway/ — メッセージングゲートウェイ、アダプタ、配信

ルートの `AGENTS.md` の上に適用されます。長文形式: `website/docs/developer-guide/gateway-internals.md`。
新しいプラットフォームアダプタ: `gateway/platforms/ADDING_A_PLATFORM.md` を順番に従ってください。

## 形状

`gateway/run.py` がファサードであり、フェーズは `run_*.py` にあります（起動、アダプタ、インバウンド、ターン、ビジー、ゴール、通知、シャットダウン、...）、セッションは `session*.py`、スラッシュハンドラは `slash_commands_*.py` ミックスイン、認可は `authz_mixin.py`、アダプタは `platforms/<name>.py` 上に `platforms/base.py` があります。ゲートウェイはユーザーYAMLを**生のまま**読み取ります（`run.py` + `config.py`）。`DEFAULT_CONFIG` 経由ではありません — CLIには見えるがゲートウェイには見えないキーは、ローダーを間違えていることを意味します（`hermes_cli/AGENTS.md`）。各アダプタは基本ツールセットを選択します（Telegram → `"messaging"`）。

スラッシュコマンド: ハンドラは `_command_handler_table` を通じて名前で検索されます。コマンドは `_IDLE_COMMANDS` または `_PLAIN_COMMANDS`（実行中でも動作）に `run_busy.py` で一覧表示されます。`if canonical == ...` チェーンはありません。レジストリ + コマンドの追加: `hermes_cli/AGENTS.md`。

## ゲートウェイには2つのメッセージガードがあります — 両方とも承認/制御コマンドをバイパスする必要があります

エージェントの実行中、受信メッセージは2つの連続するガードを通過します。(1) **ベースアダプター**(`platforms/base.py`)は、`session_key in
self._active_sessions`の場合に`_pending_messages`へキューに入れます。(2) **ランナー**(`run.py`/`run_busy.py`)は、`running_agent.interrupt()`に到達する前に`/stop`、`/new`、`/queue`、`/status`、`/approve`、`/deny`をインターセプトします。エージェントがブロックされている間(承認プロンプト)にランナーへ到達しなければならない新しいコマンドは、両方のガードをバイパスし、インラインでディスパッチされなければなりません。決して`_process_message_background()`経由では行わないでください。これはセッションのライフサイクルと競合します。

## ストリーミング配信契約(ストリームがメッセージであるアダプター)

`draft_stream_is_message = True`を持つアダプター(Slackネイティブストリーミングを中継)は、ターンごとに1つの累積ネイティブストリームを保持します。そのストリームが最終メッセージそのものです。4つの不変条件があり、それぞれが実際に発生した重複最終メッセージ事故(NS-658カナリア台帳、hermes#85796 / gateway-gateway#210)に由来します。いずれかに違反すると、重複または凍結したストリームが再発します。

1. **ドラフトフレームはプレフィックス安定である。** フレームNはフレームN+1の文字列プレフィックスでなければならない。ティックごとにドラフトを変更してはならない — フェンス閉じ（`ensure_closed_code_fences`）、カーソル接尾辞、ツール境界でのセグメント状態リセット、mrkdwn変換は禁止。非プレフィックスのフレームはスナップショット全体の再追記（「スタックコピー」）を強制する。ファイナライズ経路は実際の最終フレームを変換してもよい。

2. **コンシューマーが最終を宣言し、アダプターは推測しない。** `finish(final_text)`は完了した`final_response`（検証者フッター、完了説明を含む）を運ぶ。ストリーム後に行う新しい拡張は必ずこのペイロードに乗せること — シール後に`final_response`を変更すると`delivered_final_matches`の不一致が再発し、修正用の重複送信につながる。

3. **中間送信は`metadata["_interim_send"] = True`を運ぶ。** ターン最終でないコンシューマー側の`adapter.send()`（コメント、セグメント末尾のフラッシュ）は、それを設定するか、シール遮断が中間テキストでライブストリームをシールしてしまう。シール遮断は両方の出力ドア（`send()`と`send_for_platform()`）に存在する。新しい出力ドアには同じ2つのチェックが必要である。

4. **編集で調整し、単純送信では行わない。** シール済みストリームの隣に最終を配信するレーン（キューされたフォローアップ、メディア付き最終）は、まずコンシューマーの`message_id`に対して`edit_message`を試みる。編集可能なメッセージが存在しない場合のみ、単純な`send()`を使う。シール済みネイティブストリームは通常のメッセージであり、`chat.update`は機能する（ライブ検証済み）。

契約テスト: `tests/gateway/test_stream_final_contract.py` (ミューテーションチェック済み)。Slack の正解データ: `chat.*Stream` は mrkdwn ではなく STANDARD markdown を話す。`stopStream.markdown_text` は APPENDS。`startStream`/`stopStream` は Tier 2 (~20/分)。`draft_stream_is_message is True` を確認 — 古いテストの MagicMock アダプタは真値の属性を自動生成する。

## INFO+ ログにユーザーコンテンツを含めない

ログは `hermes debug share` アップロードに到達する: 本文、件名、表示名、アドレス、電話番号を INFO+ でログしないこと。`len(text)`、ID、`hash_for_log(chat_id)`、または `redact_phone(...)` をログする。生の値は DEBUG に送る (HX017)。

## バックグラウンドプロセス通知

`terminal(background=true, notify_on_complete=true)` はゲートウェイループ (`run_notifications.py::arm_process_watcher`) 上でウォッチャーを仕掛け、完了時に新しいターンを開始する。冗長度は `display.background_process_notifications`。注入には `admit_internal_event` のレシートが必要 (None を返すハンドラは受理ではない)。拒否された入場は、試行を消費せずに、請求されたすべてのバッチ兄弟を返金する。長文形式: `website/docs/developer-guide/gateway-internals.md` § バックグラウンドプロセス通知。

正規のローカル CLI/TUI/Desktop セッションは、人間の入力と同じ耐久性のある FIFO に完了イベントとウォッチイベントを受理する (プライベート起動ポリシー、`internal_notification` 表示種別)。オブザーバはそれらのターンを所有も消費もしない。中断された開始済みターンは不明のままとなり、後続を一時停止する。

## `/login` (ターン外、ペア DM のみ)

`GatewayLoginCommandsMixin` は、実際にペアリングされた DM 以外での実行を拒否する。ntfy、raft、a2a は
ブロードキャストでも `dm` を返す。ログインはインストール全体の `providers.nous` を設定するため、共有
ゲートウェイでは `allow_admin_from` を設定する。`anon_auth.run_sign_in` は共有プールを使わず、専用の
単一ワーカー `_login_executor` で完了まで処理する。試行はプロセスごとに1回。完了後はモデルの上書きを
保存せず、まだ `nous/welcome` を使っているエージェントを破棄する。詳しくは `gateway-internals.md` の
`/login` を参照する。

## ゲートウェイと Desktop のライフサイクル

`hermes serve` は Desktop が起動する制御プレーンで、アプリとともに終了する設計。メッセージング
ゲートウェイ（`gateway run`）はアプリが終了しても動き続ける。serve バックエンドの
`/api/gateway/*` はゲートウェイを切り離して起動する（`_spawn_hermes_action` の
`start_new_session`／`DETACHED_PROCESS`）。そのため `before-quit` の SIGTERM は届かず、
ボットは稼働を続ける。例外は更新のために Windows の venv shim を使用中のプロセスを終了する処理
（`taskkill /T /F`、#85265）。この処理は #92091 の `pause-for-update` に置き換わる。
アプリの終了とともにゲートウェイが停止する問題を、ゲートウェイをバックエンドの子に変更して
修正しない。更新時のロックを解消するために強制終了の範囲を広げない。各ゲートウェイは
`gateway_state.json`（`status.py`）に `code_sha` と `code_version` を記録し、アップデーターが
稼働中の各ゲートウェイを確認できるようにする。

## プロファイルのスコープ（アダプター、ターン、ターン間の処理）

- **受信イベントごとに1つのIDを、まず正規化する。** `gateway/session_identity.py::resolve_identity` は「どのボットがそれを受信したか／誰がそれを許可するか／どこで実行されるか」にイベントごとに1回だけ答え、ソース上に凍結された `RoutingIdentity` を固定する（ワイヤー上では見えない、`_transport_adapter_ref` と同様）。すべてのイングレス経路は、キーを導出する前に正規化シームを呼び出す。アダプター側（`platforms/base.py::_canonicalize` — `handle_message`、`_enqueue_text_event`、Telegramの写真／アルバムのルーティング、`_handle_message_while_active`、すべての `_source_session_key`）とランナー側（`run_adapters.py::_canonicalize` — プロファイル別／デフォルトのメッセージ、ビジーおよびプラットフォームイベントのハンドラー、アダプターの認証チェックコールバック、`run_inbound.py::_hm_admit_event`）の両方である。その前にはキー導出を行わない。多重化の下で未解決のID（未提供プロファイルへのルート）は、到達した最初のシームで1つのWARNINGとともに破棄され、決して `agent:main` にキー付けされない（`parked_route_refusal.drop_rejected_route`。*parked* プロファイルへのルートは、直接ボットの更新がすでに確認済みで再配信されないため、送信者にチャネル内で再送するよう伝える。リレーフレームはACKされ、同様に拒否される（`ParkedProfileRefusal`：保留されたものはACKゲート付きドレインを停滞させる）。そのトランスポートがまだ確認していないディスパッチ（例：Google ChatのHTTPイベント）は `retryable_ingress()` で実行され、代わりに `ParkedRouteRefused`（503）で応答し、その重複排除クレームを解放する）。`_transport_owner`、`_authorization_home_for_source`、`_resolve_profile_home_for_source`、`_session_key_profile`、および `_resolve_profile_for_key` は、IDが存在する場合はそれを読み取り、何も解決しなかったソース（復元された行、手動構築されたソース）に対してのみ従来のチェーンにフォールバックする。IDの隣に2つ目の答えを導出しない。オブジェクトを拡張する。`transport_profile` ≠ `runtime_profile` は正常である（共有ボット → ルーティングされたサテライト）。ソースのコピーは `session_identity.replace_source` を経由するため、IDがそれとともに移動する（`_apply_topic_recovery` も同様）。
- **受信アダプタと応答アダプタ。** `authz_mixin.py::_intake_adapter_for(source)` はイベントを
  RECEIVED したボット（ライブトランスポート参照 → リレーソケット → アイデンティティの `transport_profile`）であり、受信ポリシー（無視チャンネル、リレーの前面化、まだライブなイベントの再ディスパッチ）をゲートし、ライブな来歴を持たないソースに対しては `None` へフェイルクローズする。`_delivery_adapter_for(source)` は
  ANSWER するボット、すなわち判明している場合は受信ボット、それ以外の場合は `_adapters_for_profile` を介した `(platform,
  runtime_profile)` の唯一のオーナーである。ソースに対して `self.adapters[platform]` を読むことは決してしない。第3のリゾルバを追加することも決してしない。マトリクス（`tests/gateway/test_multiplex_transport_matrix.py`）：

  | トポロジー | ランタイム | 受信 | 配信 |
|---|---|---|---|
| 資格情報ごとのボット、ルーティングなし | オーナー | オーナーアダプター | オーナーアダプター |
| 共有資格情報 → サテライト (`profile_routes`) | ルーティングあり | 受信アダプター | 受信アダプター (再起動後は `_is_shared_bot_satellite`) |
| 共有ボット → 自前のボットを所有するプロフィール | ルーティングあり | 受信アダプター | 受信アダプター (会話の継続性; #70625 の「ルーティングされたボット」という解釈は採用されなかった) |
| セカンダリ所有のボット → `default` (`bot_profile`) | デフォルト (`agent:main`) | 受信アダプター | 受信アダプター |
| 復元済み / 手動構築、ライブの来歴なし | 保存された `source.profile` | **`None`** | `(platform, runtime)` の一意のオーナー、それ以外はそのマップの Relay (それが `fronts_platform` の場合、`_fronting_relay`、`resolve_delivery_transport` ルール); 切断されたセカンダリ → `None`、デフォルトのボットには決してならない |
- **アイデンティティはプロセスを超えて存続する。** `SessionEntry.transport_profile`（ルーティングインデックス + `sessions.transport_profile`、nullable、`SCHEMA_SQL` によって調整される）は、受信ボットをキー名前空間の隣に永続化する。名前空間はレーンがどこで「実行」されるかを示し、カラムはどのボットがそこに「配信」してよいかを示す。永続状態からセッションを復元するあらゆる処理（自動再開、ハートビート復元、プラグイン注入、バックグラウンドプロセスイベント）は、`entry.origin` から `authz_mixin.py::_restored_source` を読み取り、`session_identity.restore_identity` を介して `RoutingIdentity(transport=None)` を再固定する。その後 `_delivery_adapter_for` は、そのボットのアダプタ経由で配信するか、何も配信しない（デフォルトボットをヒューリスティックに使うことは決してない）。復元されたリレーレーンは `_fronting_relay` を使用する。復元パスは `delivery.prime_revived_egress` でイグレスをウォームアップする。このカラムを持たない行（PR-5 より前）は `_is_shared_bot_satellite` フォールバックを維持する。遅延コールバックはコマンド時点でアイデンティティ/ホームを捕捉する（`/model` ピッカー）。`_run_in_executor_with_context` はスレッドホップをまたいでスコープを運ぶ。リレー: `_with_scope` は、すべてのアウトバウンドフレームでルーティングされた `profile` をエコーし、`follow_up` はキー名前空間からそれを導出するため、コネクタは次の `passthrough_forward` にそれを刻印する。`gateway/` 内の環境依存の `get_active_profile_name()` 読み取りはブート時のみで、`# launch profile, pre-identity` とマークされる。アイデンティティを持つパスは `identity.runtime_profile` を読み取る。
- **トークンロック。** 一意の認証情報（ボットトークン、APIキー）で接続するアダプターは、`acquire_scoped_lock()` を `gateway.status` から `connect()`/`start()` および `release_scoped_lock()` を `disconnect()`/`stop()` で呼び出すため、2つのプロファイルが1つの認証情報を共有することはできません。正規の方法：`plugins/platforms/irc/adapter.py`。
- **マルチプレックス時のプロファイルスコープ環境変数読み取りは必ずフェイルクローズにすること — `os.environ` から借用してはならない**
  (`agent/secret_scope.py`; #72348, #86905)。`gateway.multiplex_profiles` の下では、`os.environ` が
  DEFAULT プロファイルの値を保持する。セカンダリプロファイルの `.env` はそのシークレットスコープ内にのみ存在し、
  `_profile_runtime_scope` によってプロファイルごとの *アクティビティ* に紐づけてバインドされる(ターン、コールバック、エビクション、ティック — 決して
  「ターンごと」だけではない)。すべてのプロファイルレベルの環境設定 — 資格情報
  (`app_secret`、トークン) および認可 (`FEISHU_ALLOWED_USERS`、`{PLATFORM}_ALLOW_ALL_USERS`、
  `GATEWAY_ALLOW_ALL_USERS`、`group_policy`、`allow_bots`) — はスコープを認識して読み取られる。アダプタは
  `gateway.platforms._shared.get_scoped_secret` 経由で(唯一の実装。アダプタはこれを
  `_get_scoped_secret` としてインポートする。`extra_or_secret` / `seed_extra_from_env` / `env_is_connected` はこれに基づいて構築される)、
  ゲートウェイの認可は `_shared.platform_gate_env` 経由で(`authz_mixin.py` が `_auth_env` としてインポートする)。スコープがインストールされ、
  マルチプレックスがアクティブな場合、スコープ内ミスは **デフォルト** を返し、決して `os.environ` を返さない(漏洩した許可リストは
  全許可チェックをスキップし、すべてのセカンダリプロファイル送信者を暗黙に拒否する、#86905)。スコープなしのデフォルトプロファイルパス
  (`UnscopedSecretError`) と単一プロファイルのデプロイでは、
  `os.environ` の読み取りを維持する — そこではそれがプロファイル自身の値である。アダプタ内でリーダーを再実装してはならない
  (`try get_secret / except UnscopedSecretError: os.getenv` の形状がミス後のフォールバック漏洩へと
  漂流する)。共有のものをインポートすること。`tests/gateway/test_shared_platform_boilerplate.py` は
  すべてのプラグインの `_env_enablement` がそれを通してのみ読み取られることを検証する。
- **スコープはターン単位ではなく、プロファイルのアクティビティ単位でバインドされます。** `run.py::_profile_runtime_scope(home)`
  （1つの`Scope`：`agent/runtime_scope.py`、HX016）がルーティングされたターン（`run_turn.py::_profile_scope_for_source`）をラップし、同じバインドが、スタック上にターンがない状態でセッションのホーム、シークレット、またはターミナルスコープに触れるすべてのパスをラップします。リリースとエビクション（`run_agent_cache.py::_run_release_in_profile_scope` — TTL、LRU、メモリプレッシャーによるエビクションはすべてこれを経由するため、`on_session_end`／メモリフラッシュは所有プロファイルのプロバイダーに到達します）、シャットダウン（`run_shutdown.py::_finalize_session`）、ターン後のメディア配信（`platforms/base.py::_media_delivery_scope`）、遅延コールバック（ピッカー、リアクション — コマンド時にルーティングされたホームをキャプチャし、コールバック内でスコープに再入場します）、通知機能、アウトバウンドWebhookです。
  所有ホームはセッションレコード（`profile_home`、`agent:<profile>:`キー）から解決し、起動プロファイルを保持する`os.environ`からは決して解決しないでください。理由：起動スコープ下でのエビクションが、セカンダリプロファイルのメモリをデフォルトプロファイルのストアに書き込んでいました。
- **`api_server` は、リクエストごとにエージェントを再構築するが、メモリプロバイダは再構築しない。** アダプタは
  `TurnRunner` とエージェントキャッシュ（リクエストごとのコールバック、モデルルート、一時プロンプト）をバイパスするため、
  `platforms/api_server_memory_sessions.py` は各セッションの初期化済み `MemoryManager` を
  リクエスト間で退避させる（`_create_agent` での排他的チェックアウト、ターンの `finally` でのチェックイン。プロファイルのホーム + `agent.session_id` をキーとする。
  アイドル/LRU による退避は、所有するホーム配下でシャットダウンする）。
  そして `AIAgent(memory_manager=...)` は、2 回目のプロバイダ初期化なしでそれを受け入れる。これがないと、前のターンの
  キューに入ったリコールが次のリクエストに到達しない（#120116）。
- **`multiplex_profiles: false` は「スコープが一切ない」という意味ではない。** 2 番目の
  プロファイルにサービスするネイティブのホスト型ルームは、アダプタが配線された後に、ゲートウェイプロセス内の
  プロセス全体のガード（`tui_gateway/launch_profile_policy.py::
  activate_multi_profile_hosting`）を反転させる。そのため、すべての
  スタンドアロンエントリポイント（`run_turn.py::_profile_scope_for_source`、プライマリアダプタのメッセージ /
  ビジー / プラットフォームイベントハンドラを `run_adapters.py::_standalone_scoped` 経由で）は、その後
  起動プロファイル自身のスコープを `run_turn.py::_standalone_launch_scope` 経由でバインドする —
  `.env` は、アクティベーション時に凍結された環境変数に基づくものであり、`.env` のみの再構築（systemd / `op run` キーにはファイルがない）でも、ライブの
  `os.environ` でもない。新しいスタンドアロンパスをそのヘルパーでゲートせよ。設定フラグではなく（#112878）。
- **フックとオブザーバは、提供されるプロファイルごとに登録される。** `agent/shell_hooks.py::register_from_config`
  とライフサイクルオブザーバは、起動時およびプロファイルの追加・削除時に各プロファイルのスコープ下で準備される。冪等性キーにはプロファイルが含まれ、`hooks/` のパスは呼び出し時に解決される（モジュール定数は最初のインポート元に固定される）。シェルフックも、ローカルセッションの作成・再開のたびに `session_policy.refresh_profile_hooks` -> `shell_hooks.sync_from_config` 経由で再同期（追加と登録解除の両方）される。これは削除を行う唯一の呼び出し元である。
- **マルチプレックス時、アダプタ YAML が `os.environ` に到達することはない。** `platforms/_shared.py::
  apply_yaml_bridge` が `PlatformConfig.extra` をシードし、セカンダリプロファイルのスコープ下では environ への書き込みをスキップする。ゲート／許可リストの読み取りは `platform_gate_env` を経由する。`if not os.getenv(X):
  os.environ[X] = …` ブリッジはプロセス全体で最初のプロファイル優先である。優先順位に触れる前に、競合するフラグを持つ 2 つのプロファイルでテストすること。
- **未提供（Unserved）は報告され、決して黙殺されない。** 共有イングレスプラットフォーム（Relay）はデフォルトプロファイルのみで動作する。追加で有効化されるものは、対処法とともに一度だけログに記録され、ランタイムステータスに刻印される（`run_adapters.py::_note_unserved_secondary_platform`）。WhatsAppブリッジはプロファイルごとに存在する。ペアリング済みのセカンダリは独自のアダプタとポートを取得し（`plugins/platforms/whatsapp/bridge_ownership.py`）、ペアリングされていないものは`whatsapp_unpaired`として報告される。また、セカンダリは自身のpidfile（pid＋開始時刻＋ポート）が識別するブリッジを採用したり通知したりすることはない。`needs_attention`は、接続パス上の単一ライター（`_update_platform_runtime_status`）で設定・解除される。
- **単一の起動元アイデンティティ。** 「このタスクはルーティングされたプロファイルにサービスを提供するか？」は、オーバーライドを`hermes_constants.get_routing_process_hermes_home()`（`agent/secret_scope.py::
  serves_routed_profile`および`_is_process_home`、`tools/environments/local.py::_is_routed_home`、`hermes_cli/env_loader.py::_process_hermes_home`）と比較する。ライブで読み取られる`os.environ["HERMES_HOME"]`とは比較しない。提供中のプロファイルを毎ターン環境変数にミラーリングする埋め込みホスト（Hermes WebUI）は、`pin_process_hermes_home()`で自身のホームを固定する。ピンがない場合、リゾルバは`get_process_hermes_home()`のまま変更されない。`get_process_hermes_home()`と直接比較する別のルーティング判断を追加しないこと。そのリゾルバはプロセスレベルのアセット用である。

## テスト

`tests/gateway/`。アダプターテストは、偽のトランスポートを使って実際の配信経路を検証する。ハードコードされたプラットフォーム一覧やコマンド数をアサートしてはならない（根本原因: 変更検出器がない）。セッションキーとガードの挙動はテストする価値のある不変条件である。プラットフォームAPIの癖は、散文ではなくコネクタのコメントとテストに記すべきである。
