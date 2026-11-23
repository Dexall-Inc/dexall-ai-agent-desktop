# cron/ (+ kanban) — スケジュールジョブとマルチエージェント作業キュー

ルートの `AGENTS.md` の上に適用されます。詳細版: `website/docs/developer-guide/cron-internals.md`。
ユーザードキュメント: `website/docs/user-guide/features/cron.md`、`kanban.md`。

## Cron

`cron/jobs.py`（ジョブストア）+ `cron/scheduler.py`（ティックループ。`scheduler_*.py` はその兄弟）。エージェントは `cronjob` ツールでスケジュールし、ユーザーは `hermes cron list|add|edit|pause|resume|run|remove` または `/cron` で行います。スケジュール形式: 継続時間（`"30m"`、`"2h"`、`"1d"`）、「every」フレーズ（`"every 2h"`、`"every monday
9am"`）、5フィールドの cron（`"0 9 * * *"`）、ISO の単発指定（`"2026-06-01T09:00:00Z"`）。ジョブごとのフィールド: `skills`、`model`/`provider` の上書き、`script`（実行前のデータ収集スクリプト。その標準出力がプロンプトに注入されます。`no_agent=True` によりスクリプトがジョブ全体になります。常に `HERMES_HOME/scripts/` 配下の FILE であり、コマンドラインではありません。`script='echo hi'` は作成時に拒否されます）、`context_from`（ジョブ A の最後の出力をジョブ B のプロンプトに連結）、`workdir`（そのディレクトリの `AGENTS.md`/`CLAUDE.md` を読み込んで実行）、`timezone`（cron 式の壁時計を IANA タイムゾーンに固定。未指定ならプロフィールのタイムゾーン）、`grace_minutes`（キャッチアップウィンドウの上書き。`0` はキャッチアップなし、cron のみ）、マルチプラットフォーム配信。

堅牢化の不変条件 — それぞれが実際の障害を防いでいる。弱めるときは、それに応える責任を負うこと:

- **非アクティブ監視** (cron エージェントセッション、`_cron_inactivity_seconds()`): デフォルトはアイドル 600 秒。`HERMES_CRON_TIMEOUT` で上書き、`0` で無制限。これは経過時間ではなくアイドル時間である — 停止したセッションは強制割り込みされ、スケジューラを独占できない。一方、長くても稼働中のジョブが打ち切られることはない。付随スクリプト (pre-run または `no_agent`) は、スクリプトのタイムアウト (`_DEFAULT_SCRIPT_TIMEOUT`、3600 秒) によって別途制限される。
- キャッチアップ窓 = 期間の半分で、120 秒〜2 時間にクランプされる。設定されている場合はジョブの `grace_minutes` が優先される (`0` = キャッチアップしない — これは実際の値であり、「未設定」ではない: `0 == False`)。見逃したワンショットには 120 秒の猶予。
- **固定された `timezone` は計算だけでなくパス全体を所有する。** `compute_next_run` は *ジョブのピン → プロファイルゾーン* を解決し、すべての `next_run_at` 書き込み箇所はピンを渡さなければならない (`cron/jobs.py` 呼び出し箇所、`quota_hold.plan_hold`、`unreachable_retry.will_retry`、`extra_fire.settle`)。1 箇所でも見逃すと、バーストの再実行またはスロットのスキップになる。`_evaluate_due_job` は保存されたインスタントをジョブのゾーンに正規化し、固定ジョブでは `_repair_timezone_shifted_cron` を**スキップ**する — その修復はプロファイルゾーンに従うジョブのためのものであり、固定ジョブではその壁時計述語が到来した発生を未来として読み取り、それを過ぎて再アンカーする (ジョブは静かに発火しない)。ノブは `cron/jobs_time.py` にあり、`timezone`/`grace_minutes` は `job_definition.JOB_DEFINITION_FIELDS` に留まらなければならない。さもなければプロファイル配布がそれらを剥ぎ取る。
- すべての再発事象が計上される。`tick()` はディスパッチの**前**に `next_run_at` を進める（実行途中のクラッシュをまたいでも at-most-once を保証）とともに、同じ保存内で `pending_slot` を刻印する。刻印を発見しつつオーナーが死んでいるスキャンは、ONCE の即時復元（`cron/occurrences.py`）を行い、実行台帳の `scheduled_instant` が2回目の発火をブロックし、`cron.catch_up_missed: false` は猶予期間を過ぎたミスをログ付きの理由でスキップする。スロットを黙って落とすことは決してしない（#107485）。
- プロファイル単位のティックロック `<home>/cron/.tick.lock` は、そのプロファイルのストアについてプロセス間での重複ティックを防ぐ。`~/.hermes/...` リテラルは決して使わない。
- **ヘッドレスのティックは拒否し、決して起動しない。** `hermes cron tick`（システム crontab / 外部スケジューラ）は `tick(headless=True)` を呼び出し、`cron/scheduler_gateway_gate.py` は、ディスカバリがそのホームを所有するゲートウェイなしと判断した場合（`last_fire_error` を刻印、ティックごとに1回の警告、期限到来分には触れない）に、`run_canonical_job → connect_gateway → ensure_gateway_runtime` が管理外のデーモンを起動するのを許さず、エージェントジョブをスキップする。承認と同じ方針（ヘッドレス / cron = 拒否）。プロセス内ティッカーと `hermes cron run` はヘッドレスではない。
- **ティッカーは、ティック全体（ループ前のコードを含む）にわたって、提供される各プロファイルのスコープをバインドします。**
  `scheduler_provider.py::_start_multiplex` は `profiles_to_serve()` を `_profile_cron_scope(home)`（ホーム＋シークレットスコープ＋ターミナルスコープ）の下で順次反復する **1つの** ティッカーであり、N 個のスレッドではありません（モジュールグローバルが競合します）。ティックが触れるすべてのものはそのガード内に存在します：ストアのオープン、ロックパス、バックオフ／失敗カウンタ（`_note_tick_failure`）、ジョブ環境の構築、完了ジョブの `on_session_end` フラッシュ。監視（`scheduler_thread.py::
  SupervisedTickerThread`；ゲートウェイ起動時に開始し、別のゲートウェイが既に提供しているホームでは待機し、プロファイルディレクトリが出現またはトゥームストーン化されたときに再列挙）はプロセス単位ではなく、提供されるホームごとに行われます。理由：スコープに入る前にオープンされたストアが、起動プロファイルの `jobs.json` にセカンダリプロファイルの実行レコードを書き込んでいました。
- **Cron の所有権は `gateway.multiplex_profiles` にゲートされません。** そのフラグはアダプタをゲートします。どちらの場合でも、1つのホストゲートウェイプロセスがすべてのプロファイルのストアをティックします（`run.py::_cron_tick_profile_homes`）。ティックセットをそれにゲートすると、ティッカーが訪問しないストアに、起動プロファイル以外のすべてのプロファイルのジョブが残されていました。
- **プロファイル単位のプロセス前提がバグの温床である。** 1つのプロセスがN個のホームを刻むため、「このプロセスのプロファイル」を基準にしたものはすべて誤りとなる。すなわち、進行中状態（`_running_job_ids`、`_running_since`、`_running_futures`、`_running_worker_pids`、`_running_fire_owners`、`_interrupted_job_ids`）は`_inflight_key(job_id)` = `(home key, job id)`をキーとしており、2つのプロファイルが正当に`daily-brief`を保持し得る。並列プールはホームをキーとする（`cron.max_parallel_jobs`はプロファイル単位）。また、古いコードのyieldゲートは、プロセス全体のランタイムロック真偽値ではなく`scheduler_ownership.owns_cron_tick_for(home)` / `live_gateway_ticking(home)`を問い合わせる。公開アクセサ（`get_running_job_ids`、`get_running_job_details`、`get_wedged_job_ids`）は、シャットダウンドレイン用にホスト全体のベアジョブIDの和集合を依然として報告するが、LIVENESSの消費者（`jobs.py::_job_running_in_this_process`、`tools/cronjob_tools`）は`is_job_running(job_id, home=...)`を問い合わせる。この和集合により、プロファイルAで実行中の`daily-brief`が、プロファイルBのアイドル状態のものに対する応答を担ってしまう。
- **クレームは、登録されたキーで解放される。** cronスコープはContextVarである。`try_register_running_job`は`_profile_cron_scope`内のティッカースレッド上で実行される一方、プールワーカーの`finally`は`ctx.run`の外側にあり、LAUNCHホームを解決する。登録元のホーム（`release_running_job(job_id, home=...)`）を渡さないと、すべてのセカンダリプロファイルのクレームが漏れる。ジョブは、強制解放のバックストップがそれを掃除するまで発火ウィンドウをスキップし、ドレインは幽霊のような作業を目にする。キーの半分からホームを再構築してはならない（`Path(key[0])`）。`hermes_home_key`は正規化を行うため、`_inflight_home_path`を使うこと。
- **ティックされたホームの状態は、ホームがセットから外れると回収される。** `register_ticked_homes`は毎サイクル再公開され、離脱したホームのパラレルプールを刈り取る。プールはかつて`atexit`まで存続していたため、ティックされた各ホームはThreadPoolExecutorとそのワーカースレッドを永久に保持していた。
- **ホストゲートウェイは、自身のゲートウェイを実行するプロファイルに対して待機状態になる。** `run.py::
  _cron_profile_gate`（`hermes_cli/web_server.py`が通過するのと同じゲート）は、起動プロセスとプロファイルごとのゲートウェイを1つのストア上に保つ。ティックロックは同時二重実行を防ぐが、競合は防げない。起動プロセスが勝った場合、配信はそのプロファイルのライブアダプタではなく`SharedRouteAdapters`/フェイルクローズ経由で行われる。ゲートはliveness PIDを`os.getpid()`と比較する。このプロセスは起動用の`gateway.pid`を保持し、かつ提供されるすべてのプロファイルを`served_profiles`に公開するため、素のliveness応答ではホスト全体でcronを停止させてしまう。
- **再起動に耐える外部ワーカーは自らを起動する。** `_launch_external_cron_worker` はチェックアウトを固定し、PM インストール時にはコミット済み世代の `site-packages` も子の `PYTHONPATH` 上で固定して `_HERMES_CRON_WORKER_BOOT` とマークする。子のパッケージエントリ（`cron/__init__.py` → `cron/worker_bootstrap.py`。`cron.jobs` インポートより前 — `-m
  cron.scheduler` が先にパッケージを実行する）は、その後 PM の `activate_dependencies` を実行する。これはコミット済み世代をワーカーの存続期間にわたってリースし、その `.pth` ファイルを実行し、最初のサードパーティ製インポートより前にそれを有効化する。有効化の失敗は致命的である。ワーカーは所有権の ack の前に終了する（報告されたディスパッチ失敗）が、コレクタが削除し得る未リース世代上で実行されることはない。ゲートウェイはブートを再実行しない — `hermes_bootstrap` が自らの起動時にすでに実行している（#122222）。ワーカーの `__main__` は `hermes_bootstrap`（`finish_worker_boot`）をインポートし、ペイロードを読み取る前に `run_agent` の中断プル復旧を実行し、その後にのみマーカーを落とす。ソース更新による再起動（`-I`、`PYTHONPATH` なし）または復元後の再実行は、ワーカー全体を再生しなければならず、ペイロードが消え依存関係のブートもない状態で ack の後に着地してはならない。
- Cron セッションは `skip_memory=True` を渡す。メモリプロバイダは cron 中には意図的に実行されない。
- Cron実行には専用のセッションがあります。継続可能な配信は、返信向けの会話をミラーリングまたはシードすることができます。オリジン、オリジンなしのホームフォールバック、ユーザー作成のベアプラットフォームホーム、またはオプトインした明示的なターゲットです。`all`の展開はホームミラーリングの対象になりません。ミラーリングされたブリーフは、ターン境界で追加されるユーザーターンとしてラベル付けされ、ロールの交互を維持します。
- cronティッカーは、`HERMES_DESKTOP=1`のときにデスクトップ起動のバックエンドで実行されます。この環境変数は「アプリによって起動された」ことを意味し、「GUIが監視している」ことを意味するものではありません（ルート: 機能はセッションのプロパティです）。
- バックグラウンドの`delegate_task`はプロセスローカルです。再起動後も存続する必要がある処理は、cronジョブまたは`terminal(background=True, notify_on_complete=True)`プロセスです。

## カンバン（マルチエージェント作業キュー）

複数のプロフィール／ワーカーが協働できる、SQLiteに永続化されたボード。ユーザー: `hermes kanban
<verb>`。ディスパッチャーが生成したワーカーは専用の`kanban_*`ツールセットを使用するため、カンバンタスクの外ではスキーマのフットプリントがゼロになる（フットプリントラダーの段階3）。

- **CLI:** `hermes_cli/kanban.py` ファサード + 14 個の `kanban_*.py` 兄弟（`boards`、`db`、`db_connect`、
  `db_dispatch`、`db_notify`、`db_graph`（タスク初期化と分解）、`workspace`、...）。動詞: `init, create, list (ls), show, assign, link,
  unlink, comment, attach, attachments, attach-rm, complete, request-review, request-changes,
  reopen-review, block, unblock, archive, tail`、および `watch, stats, runs, log, assignees, heartbeat,
  notify-*, dispatch, daemon, gc`。Argparse のエイリアスディスパッチは `list` と `ls`（ルート）の両方を受け付ける必要があります。
- **ツールセット:** `tools/kanban_tools.py` — `kanban_show, kanban_complete, kanban_request_review,
  kanban_request_changes, kanban_block, kanban_schedule, kanban_heartbeat, kanban_comment,
  kanban_create, kanban_link,
  kanban_attach, kanban_attach_url, kanban_attachments`;保存された選択が `kanban` を有効にするプラットフォーム（`hermes tools enable kanban --platform <p>`;デフォルトオフ、`CONFIGURABLE_TOOLSETS` 内）は、ボードルーティング用の `kanban_list`/`kanban_unblock` に加えてフルセットを取得します。check_fn はスキーマビルド自身の選択（`tools/kanban_toolset_context.py`）を読み取り、レガシーのトップレベル `toolsets` キーだけを読み取りません。
- **ディスパッチャ:** 期限切れのクレームを回収し、準備完了タスクを昇格し、アトミックにクレームし、割り当てられたプロファイルを起動する常駐ループ（デフォルト 60 秒）。デフォルトでは**ゲートウェイ内**で実行されます（`kanban.dispatch_in_gateway: true`）。スタンドアロン: `plugins/kanban/systemd/hermes-kanban-dispatcher.service`。
- **プラグインアセット:** `plugins/kanban/dashboard/`（Web UI）+ systemd ユニット。`kanban_db.connect` はそれ自体の接続ヘルパーです — `projects_db.connect`（パス近接ジェネレーターが行った）にエイリアスしないでください。

隔離: **board** はハードな境界です — ワーカーは環境に `HERMES_KANBAN_BOARD` が固定され、他の board を見ることはできません。**tenant** は board 内のソフトな名前空間です (ワークスペースパス + メモリキーによる分離で、1つのフリートが複数のビジネスにサービスを提供します)。タスクに対する連続した非成功試行が `kanban.failure_limit` 回 (デフォルト 2) に達すると、ディスパッチャはスピンループを止めるためにそのタスクを自動的にブロックします。ワーカーの終了コード `KANBAN_TERMINAL_PROVIDER_EXIT_CODE` (78 — 資格情報の失効、モデルの消滅。ワーカー自身の `failure_reason` による `cli._TERMINAL_PROVIDER_REASONS` 経由の分類) は、最初の試行でそれをトリガーし、スティッキーに保持されます。なぜなら、いかなる再試行でもそれを回復できないからです (#114587)。

プロセス識別に関する注意: `kanban --preserve-cache` には "serve" が含まれます — argv の部分文字列でプロセスを分類しないでください (root)。ワーカーの生存確認は `(worker_pid, worker_started_at)` です — クレーム時に記録された開始時刻フィンガープリント (`gateway.status.get_process_start_time`) であり、単なる PID の存在ではありません。そうしないと、再利用された PID がリクレーム時に強制終了されてしまいます。

- **通知はタスクを所有するプロフィールを通じて送信される。** `hermes_cli/kanban_db_notify.py`
  サブスクリプションはプロフィールを保持し、`gateway/kanban_watchers_notifier.py` はその
  プロフィールのアダプターを通じて、そのスコープ（`_notify_profile_filter`）の下で配信される。マルチプレクサーの起動
  アダプター経由ではない。フェイルクローズのスキップは WARNING で一度だけログに記録され、対処法が示される。単なる `continue` ではない。
  ディスパッチされたワーカーには `HERMES_KANBAN_BOARD` と、割り当て先の `HERMES_HOME` が
  サニタイズされた子環境（`build_subprocess_env` + `strip_launch_profile_env`）に固定される。デフォルト
  プロフィールの `.env` を継承することはない。
- **プロンプトインジェクションの発生箇所は、ツールアクセスではなく所有権でゲートされる。** ツールアクセス（プロフィールのツールセットで見える `kanban_show`）と
  継承された `HERMES_KANBAN_TASK`（委譲された子、ワーカーの隣で実行される cron 実行）は
  所有権ではない。カンバンのガイダンス（`agent_init`、`system_prompt` フォールバック）と
  停止のナッジは `agent/delegation_context.py::owned_kanban_task()` を介してタスクを解決する。他のリーダーは
  環境の読み取りを `is_dispatcher_owned_worker_context()` と組み合わせる。
- **子孫フェンスはフラグではなくパスである。** 委譲された子のカンバンマーカー
  （`agent/delegation_context.py::DELEGATED_CHILD_ENV_MARKER`）はフェンスされたボードの ROOT を保持する。
  `kanban_path_is_fenced(path)` は、ディスパッチャーが固定した `HERMES_KANBAN_DB` 上、または
  そのルート配下でのみ変更を拒否する。したがって、スクラッチの `HERMES_HOME` に対して作業する子は
  書き込み可能なボードを維持する。

## テスト

`tests/cron/`、`tests/hermes_cli/test_kanban*.py`、`tests/tools/test_kanban*.py`。スケジュール解析とキャッチアップウィンドウは純粋関数です。データとしてテストしてください。動詞リストやツールセットのサイズをアサートしないでください（root: 変更検出器なし）。時間ベースのテストでは緩い境界（≥ 2秒）とイベント同期を使用してください。
