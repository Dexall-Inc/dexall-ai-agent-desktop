# agent/ — AIAgent、ターンループ、プロンプト、圧縮

ルートの `AGENTS.md`（プロンプトキャッシュの不変条件、パッケージおよび Python の構造ルール）の上に適用される。

## 構造

`run_agent.py` が公開ファサードである。`AIAgent` はミックスイン（`agent/turn_facade.py`、
`client_lifecycle.py`、`stream_delivery.py`、`session_persistence.py`、`compression_facade.py`、...）から組み立てられる。
構築は `agent/agent_init.py::init_agent` が実行し、1ターンは
`agent/conversation_loop.py::run_conversation` であり、`AIAgent.run_conversation` はセッションのターンリースを取得した後に
それを転送する（`turn_facade_lease.py`）。`AIAgent.__init__` は約60個のパラメータ（資格情報、ルーティング、コールバック、セッションコンテキスト、予算、資格情報プール、...）を受け取る。
一覧は `run_agent.py` を読むこと。通常触るサブセット: `base_url`、`api_key`、`provider`、
`api_mode`（`"chat_completions" | "codex_responses" | ...`）、`model`（空 → 後で config/provider から解決）、
`max_iterations`（デフォルト 500、サブエージェントと共有）、
`enabled_toolsets`/`disabled_toolsets`、`quiet_mode`、`save_trajectories`、`platform`
（`"cli"`、`"telegram"`、...）、`session_id`、`skip_context_files`、`skip_memory`、`credential_pool`。
`chat(message) -> str` がシンプルなインターフェース。`run_conversation(user_message, system_message=None,
conversation_history=None, task_id=None) -> dict` は `final_response` と `messages` を返す。

## エージェントループ（`agent/conversation_loop.py` + `agent/turn_*.py`）

完全に同期で、割り込みチェック、予算追跡、1ターンの猶予呼び出しを備える:

```python
while (api_call_count < self.max_iterations and self.iteration_budget.remaining > 0) \
        or self._budget_grace_call:
    if self._interrupt_requested: break
    response = client.chat.completions.create(model=model, messages=messages, tools=tool_schemas)
    if response.tool_calls:
        for tc in response.tool_calls:
            messages.append(tool_result_message(handle_function_call(tc.name, tc.args, task_id)))
        api_call_count += 1
    else:
        return response.content
```

イテレーションの各フェーズはそれぞれ独立したファイルなので、（たとえば）オーバーフロー処理の変更は1つの
約600行のファイルに触れるだけで済む: `turn_preflight*`、`turn_iteration_prep`、`turn_request_assembly`/`turn_api_request`、
`turn_api_call`、`turn_api_error`、`turn_response_intake`/`turn_response_check`、
`turn_empty_response`、`turn_tool_round`/`turn_tool_validation`、`turn_overflow`、
`turn_truncation`、`turn_scripted_prelude`（プロンプト組み込みが最初のモデル呼び出しの前に実行するツール呼び出し）、
`turn_context_compaction`、`turn_recovery`、`turn_recovery_autorecover`
（枯渇後の待機・再試行ラダー）、`turn_retry_state`、
`turn_stop_gates`、`turn_liveness`、`turn_usage`、`turn_final_response`、`turn_finalizer`、
`turn_summary`。`agent/` 内で `search_files` を使って `def X`、`file_glob="turn_*.py"` でフェーズを探す。

メッセージは OpenAI 形式 `{"role": "system|user|assistant|tool", ...}` を使用。推論内容は
`assistant_msg["reasoning"]` に格納される。

**エージェントレベルのツール**（`todo`、`memory`、...）は `agent/tool_executor.py` が
`agent/inline_tool_executors.py` の `INLINE_TOOL_EXECUTORS` テーブルを通じて `handle_function_call()` の前に
インターセプトする。追加するにはそのテーブルに登録する（`if name == ...` の連鎖は使わない）。`tools/todo_tool.py` がパターン。

## メッセージフローの不変条件（すべての変更はこれらと照合してレビューされる）

- **プロンプトキャッシュを壊してはならない。** 過去のコンテキストを変更したり、ツールセットを変更したり、メモリを再読み込みしたり、
  会話の途中でシステムプロンプトを再構築したりしてはならない。システムプロンプトは会話の存続期間中バイト単位で安定しており、
  唯一のコンテキスト変更は圧縮である。会話途中で何かを注入する必要があるものは、システムプロンプトではなく
  **ユーザーメッセージまたはツール結果**に載せる: スキルスラッシュコマンド（`agent/skill_commands.py`）はユーザーメッセージとして注入し、
  サブディレクトリ `AGENTS.md` のヒント（`agent/subdirectory_hints.py`）はツール結果に追記する（`_MAX_HINT_CHARS = 32_000` を超えると先頭+末尾を切り詰める。
  切り詰めはログに記録され、チャットのステータス警告としてキューに入れられることはない — `context_file_max_chars` はその上限を引き上げない）。
- **厳密なロール交互。** 同じロールのメッセージを連続させてはならない。ループ途中に合成ユーザー
  メッセージを注入してはならない。唯一の例外は `/steer` で、ツール結果の後に独立したユーザー行として配信される
  （`assistant(tool_calls) → tool → user` はすべてのプロバイダ経路で合法）—
  すでに永続化されたツール行に塗り付けてはならない。追記専用の永続化では、ライブリクエストと乖離したままになるからだ。
  このため Cron 配信は独自のセッションに置かれる。
- **コンテキストファイル**（`agent/prompt_builder.py`）は起動時に CWD からのみ読み込み、上限がある
  （`CONTEXT_FILE_MAX_CHARS` / コンテキストウィンドウからの動的上限 / `context_file_max_chars`）。
  インストールツリーの `AGENTS.md` をプロジェクトコンテキストとして読み込んではならない（PR #64611）。サブディレクトリのヒントは
  作業ディレクトリ外のパスを拒否するので `~/.codex/AGENTS.md` / `~/.claude/CLAUDE.md` が混入することはない。
- **`_last_resolved_tool_names` は `model_tools.py` のプロセスグローバルである。** `tools/delegate_tool.py` の
  `_run_single_child()` はサブエージェント実行の前後でこれを保存/復元する。これを読むコードは子の実行中に
  一時的に古い値を見る可能性がある。

## 圧縮（`agent/compression_facade.py`、`conversation_compression.py`、`turn_context_compaction.py`）

すべてのサーフェス（CLI、ゲートウェイ、TUI、ACP）での手動 `/compress` は
`agent/conversation_compression_manual.py::compress_now` を通る（`here [N]` / focus /
`--preview` / `--aggressive` のための1つのパーサ。サーフェスは自分の argv だけを解析し、`after_messages` をインストールして描画する）。

2つの層がある: ゲートウェイのセッション衛生（85% しきい値）とエージェントの `ContextCompressor`（50%、
設定可能。モデルごとの上書きあり。プロバイダが証明したオーバーフロー後の失敗クールダウン）。アルゴリズムは
まず古いツール結果を刈り取り（LLM 呼び出しなし）、次に境界を選び、`auxiliary` 圧縮モデルで構造化サマリーを生成する。
インプレース圧縮は単一の安定したセッション id を維持する。ネイティブの Responses/Codex 圧縮経路はプロバイダ固有である。
停滞したサマリーストリームは `auxiliary.compression.fallback_chain` で一度再試行し、繰り返しの停滞（すでにクールダウンラダーにある停滞クラスの失敗）は
同じパイプラインを通る決定的フォールバックサマリーで終わる — リース/フェンスの外でコミットされた刈り取りは決して行わない。
圧縮は認可されたキャッシュ破壊であり、唯一のものとして維持すること。詳細:
`website/docs/developer-guide/context-compression-and-caching.md`。

## モデルとプロバイダの解決

- 実行時のプロバイダ/モデル解決とその優先順位: `website/docs/developer-guide/provider-runtime.md`。
  プロバイダプロファイルはプラグイン（`plugins/model-providers/<name>/`、`plugins/AGENTS.md` 参照）。
  `agent/model_metadata.py` がコンテキスト長と能力を保持する。
- **補助（サイド LLM）処理** — キュレーター、ビジョン、埋め込み、タイトル生成、session_search、
  圧縮 — は `agent/auxiliary_client.py::_resolve_auto_route` で解決される。各タスクは config.yaml の `auxiliary:` で
  独自の `provider/model/base_url/reasoning_effort` を固定できる。
  物理的な試行はすべて `_relay_sync_completion` / `_relay_async_completion` /
  `_relay_sync_stream` に集約され、`agent/auxiliary_hooks.py` が `pre_auxiliary_call` /
  `post_auxiliary_call`（オブザーバーのみ、フェイルオープン、`aux_task` セット）を発行する。メインループの
  `pre/post_api_request` イベントは補助呼び出しでは発火させてはならない（#79733）。
- フォールバックモデルと資格情報プールは解決チェーンのコードである。モックではなく一時 `HERMES_HOME` に対する
  実インポートで E2E すること（ルートのルーブリック）。

## i18n（`agent/i18n.py` + `i18n_layers.py` + `i18n_languages.py`）

`t(key)` はプラグインパック（最後に登録されたものが優先）→ ユーザーオーバーレイ `<home>/locales/<lang>.yaml`
（プロファイルスコープ）→ バンドル済み `locales/<lang>.yaml` → 同じものを `en` で → 素のキー、の順に解決する。各層はフラットな
ドット区切りキーで、部分的なものでよい。`(home, lang)` ごとに1つのマージ済み辞書がキャッシュされ、`reset_language_cache()`
（すべてのパック登録と `config set display.language` で呼ばれる）がすべてを破棄する。
`supported_languages()` がライブな集合（バンドル ∪ オーバーレイ ∪ パック）であり、`display.language`
検証と `_normalize_lang` が受け入れるもの。`SUPPORTED_LANGUAGES` はバンドル済みタプルのまま。`.tui.yaml` /
`.desktop.yaml` パックファイルはここでは解析/フラット化/提供（`surface_catalog`、RPC
`i18n.catalog`）以外では不透明である。`tui` サーフェスではバンドル済み `locales/<lang>.tui.yaml` が
`surface_catalog` が提供するものの最下層である（TUI は TS では英語のみを出荷する）。バンドル済み id の内名は `i18n_languages.py` にあり、
`apps/shared/src/i18n.ts` と一致しなければならない。

## メモリ、コンテキストエンジン、キュレーター

`agent/memory_provider.py`（ABC）+ `agent/memory_manager.py`（オーケストレーター）がメモリプロバイダ
プラグインを駆動する。`agent/context_engine.py` がコンテキストエンジンプラグインを、`agent/image_gen_provider.py` が
画像生成プラグインを駆動する（すべて `plugins/AGENTS.md` に記載）。`agent/curator.py` + `curator_backup.py` が
スキルキュレーターを実装する（`skills/AGENTS.md`）。Cron セッションはデフォルトで `skip_memory=True` を渡す —
メモリプロバイダは cron 中は意図的に実行されない。

- セッション終了時のメモリ抽出とプロバイダの `on_session_end` は、セッションが終了する場所（ターン、
  退避、シャットダウン、`tui_gateway` のティアダウン）で実行され、呼び出し元が先に所有プロファイルのスコープを
  バインドする（`_run_release_in_profile_scope`、`_session_profile_runtime_scope`）。エージェントはフラッシュ時に
  `os.environ` から自ホームを導出しない（`Path(_session_db.db_path).parent` が正）。
  プロバイダのバックグラウンド処理は `memory_provider.py::spawn_context_thread`（contextvars をコピー）を通じて開始され、
  素の `threading.Thread` は使わない。`title_generator.py` がその形。
- `agent/secret_scope.py::get_secret` は `set_multiplex_active(True)` の後でのみフェイルクローズ（`UnscopedSecretError`）する。
  ゲートウェイ、cron、migrate、`serve` がそれを設定する。新しいマルチホームホストも設定しなければならず、
  さもなければすべてのガードが黙って無効になる。分離はプロファイル間であり、子は `copy_context` で継承する。
  子の `UnscopedSecretError` はスポーンサイトのバグであり、`os.getenv` へのフォールスルーの根拠にはならない。
  委譲された子は `delegation_context.py::DELEGATED_CHILD_ENV_MARKER` を運び、その値はフェンスされたカンバンボードのルートであり、
  素のフラグではない。

## テスト

ループ/フェーズのテストは `tests/agent/` に置く。フェーズが実際に読むバインディングをパッチすること。
プロンプトテキストのスナップショットではなく、メッセージ形状の不変条件（交互、バイト安定のシステムプロンプト）を検証すること。

長文: `website/docs/developer-guide/agent-loop.md`、`prompt-assembly.md`、
`context-compression-and-caching.md`、`provider-runtime.md`、`session-storage.md`、
`subagent-lifecycle-api.md`。