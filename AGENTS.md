# Hermes Agent - 開発ガイド

このルートファイルはハブです。どこにでも適用される内容と、その後のルーティングテーブルで構成されています。各エリアの `AGENTS.md` は、そのディレクトリで作業するときに自動的に読み込まれるため、そこで編集する前に読んでください。
`python scripts/check` はこのファイルを 12k 文字、ルートから各エリアへの連鎖を 30k 文字に制限します。長文は `website/docs/developer-guide/` に置いてください。

※開発に関する議論はデフォルトで日本語で行います。

**正しい解決策を決して諦めない。**

## Hermes とは

Hermes は、1 つのエージェントコアを CLI、TUI、Electron デスクトップアプリ、Web ダッシュボード、ACP エディタ、メッセージングゲートウェイ（25 以上のプラットフォームプラグイン）で動かすパーソナル AI エージェントです。コアを肥大化させるのではなく、**プラグインとスキル**によって拡張されます。

ほぼすべての設計判断を形作り、あらゆる変更をレビューする際の視点となる 2 つの不変条件があります。

- **会話ごとのプロンプトキャッシュを維持する。** 過去のコンテキストを変更したり、ツールセットを差し替えたり、メモリを再読み込みしたり、会話の途中でシステムプロンプトを再構築したりすると、キャッシュされたプレフィックスが壊れ、ユーザーのコストが倍増します。唯一の例外はコンテキスト圧縮です。システムプロンプトの状態を変更するスラッシュコマンドは次のセッションに延期され、オプトインの `--now`（`/skills install --now`）が用意されています。
- **コアの役割を絞り、機能は周辺コンポーネントに持たせます。** すべてのモデルツールは毎回の API 呼び出しで送信されるため、新しい *コア* ツールの基準は高く設定されています。新しい能力は、CLI コマンド + スキル、サービスゲート付きツール、またはプラグインとして追加すべきであり、コアの表面として追加すべきではありません。

標準システムプロンプトまたは `tools[]` への変更は、`scripts/ci/prompt_surface.py render` が一緒にコミットされるまで `tests/ci/test_prompt_surface.py` に失敗し、そのスナップショット（`tests/fixtures/prompt_surface/`）はマージに hermes-agent-core の承認が必要です。

## コントリビューションルーブリック

このプロジェクトの意図レイヤーであり、コントリビューターとトリアージスイーパー（`implemented_on_main`、`cannot_reproduce`、`incoherent` のみでクローズ可能。趣味ベースのクローズはメンテナーの判断であり、迷った場合は PR は開いたままにします）のためのものです。長文と例は `website/docs/developer-guide/contributing.md` § コントリビューションルーブリックを参照してください。

**歓迎されるもの:** 実際のバグ修正（`main` での再現、正確な行、兄弟パスを含むクラス全体）。エッジでの到達（アダプタ、プロバイダ、モデル、UI 機能）を既存のセットアップ UX に配線すること。god-file → モジュールへのリファクタリング。複製する前に拡張すること（1 カテゴリに 3 つ以上の PR → ABC + オーケストレータ）。挙動契約テスト。一時的な `HERMES_HOME` に対する実際のインポートを使った E2E（解決、設定、セキュリティ、I/O 変更）。著作者が生き残るように cherry-pick による救済。

**よく作られていても却下されるもの:** 具体的な消費者がいないフック。非シークレット設定用の新しい `HERMES_*` 環境変数（`.env` はシークレット専用、挙動は `config.yaml` に置く）。ターミナル + ファイルまたはスキルで既に実現できる場合の新しいコアツール。指示ツールに対する `offset`/`limit` ページネーション。保護する機能を破壊する「修正」。オプトインゲートのないアウトバウンドテレメトリ。変更検出テスト。コアファイルに触れるプラグイン。コアツリー内のサードパーティ製品（スタンドアロンのプラグインリポジトリを出荷する）。

**バグと呼ぶ前に、** 主張と意図の両方を検証してください（`git log -p -S "<symbol>"`）。分離はしばしば設計です（プロファイルは意図的に島です）。欠如が荷重を支えている場合があり、バグが現れる行を指し示せない修正は未検証の前提を持っています。

**セキュリティ:** `SECURITY.md` がスコープの権威です。§3.1 の指摘は非公開にします（GitHub Security Advisories または security@nousresearch.com）。公開の issue、PR、コミット、コメントには決して入れません。§3.2 のハードニングは通常の公開作業です。越えた §2 の境界を、`main` での再現とともに明記してください。

**フットプリントラダー**（それを解決する最も高い段を取る）: 既存コードの拡張 → CLI コマンド + スキル → サービスゲート付きツール（`check_fn` が到達可能性/オプトインに答える。セッションごとの表面にはしない）→ プラグイン → カタログ内の MCP サーバー → 新しいコアツール（根本的で、広く有用で、それ以外では到達不能なもの）。

## 開発環境

`source ./activate`（`activate.fish`、`activate.ps1`）は PM 環境をプロビジョニングしてアクティブ化します。最初に分離された `HERMES_HOME`/`HERMES_RUNTIME_DIR` を選んでください（`website/docs/reference/package-management.md#developer-workflow`）。テストには `CONTRIBUTING.md` にある別のテスト環境が必要です。**`python scripts/check`**（`just check`）は CI が実行するすべてのブロッキング lint チェックを、CI の固定ツールで実行します。`--install-hook pre-push` はプッシュのたびにそれを実行します（プル後に再実行してフックを更新してください）。`just` はすべての開発者コマンドを一覧表示します（lefthook は同じレシピを呼び出します）。新しいコマンドは `scripts/` ファイルとレシピで構成されます。`HX0xx`/`PS-P0x` ルールとその修正は `scripts/code_health/config.py` にあります。`# noqa` は指摘を免除しません。`# health: allow <RULE> -- <why>` がそれを免除します。

## プロジェクト構造

ファイルシステムが正典です。荷重を支えるエントリポイント:

```
hermes-agent/
├── run_agent.py          # AIAgent ファサード。ターンループは agent/turn_*.py にある
├── model_tools.py        # ツールオーケストレーション、handle_function_call()。発見は tools/registry.py
├── toolsets.py           # TOOLSETS 辞書、_HERMES_CORE_TOOLS
├── cli.py                # HermesCLI（REPL、スラッシュディスパッチ）+ hermes_cli/cli_*_mixin.py
├── persistence/          # ストレージインターフェースとその sqlite/ バックエンド
├── hermes_constants.py   # get_hermes_home()、display_hermes_home() — プロファイル対応パス
├── scripts/              # check、run_tests.sh、code_health/、ci/
├── evals/                # ライブモデル A/B とプローブハーネス
└── website/              # Docusaurus ドキュメント（developer-guide/ に長文のエリアドキュメントがある）
```

**ユーザー状態:** `~/.hermes/config.yaml`（設定）、`.env`（シークレットのみ）、`logs/`（`hermes logs`）。すべて `get_hermes_home()` でプロファイル対応。

### パッケージと Python の形

トピックがファイルを超えて成長したらフォルダになります。`<stem>/__init__.py` は**ファサード**です（その docstring が各モジュールの役割を命名し、`__all__` が表面であり、PEP 562 の `__getattr__` は測定された起動コストまたはそれが命名するインポートハザードのためだけに使います。挙動はありません。`tools/connectors/` がそのモデルです）。`<stem>/<topic>.py` がコードを保持します。フラットな `<stem>_<topic>.py` の兄弟（`gateway/run.py`、`tools/mcp_tool.py`）は触られるまで残ります。エリアの `AGENTS.md` がまだそれを規定していない限り追加しないでください（`tui_gateway` の RPC メソッド、`tools/` のバックエンド）。ファミリーフォルダは ABC/Protocol、バリアントごとに 1 モジュール、名前 → バリアントのテーブルを保持します（`tools/environments/`、そのテーブルはまだ `terminal_tool_backends.py` にあります）。ツールフォルダは `tool.py` から登録します。テストはフォルダをミラーします。

- **トピックでコードを探す:** `search_files` で `<stem>/` と `<stem>_*.py` 内の `def name` を検索します。ファサードではなく。
- **インポートはモジュールの先頭に:** トピックモジュールは相互にインポートし、ファサードは決してインポートしません。循環は共有名がより低いモジュールに属することを意味します。名前が検索される場所にパッチを当ててください。
- **サイズと複雑さはユニットごとにラチェットされます:** 新しい関数は CC ≤ 20、≤ 300 行、ネスト ≤ 6。ファイルは ≤ 2,000 行。既に超過しているユニットは減る方向のみ（コードを `<stem>/` に移動）。
- **形:** コードは 3.11 でインポートします（PEP 695 構文なし）。インポートはツール登録以外に副作用を持ちません（I/O、スレッド、設定、環境変数の読み取りなし）。入力は、凍結 dataclass、`Enum`、`Literal`、またはエリアのワイヤモデル（`tui_gateway` では Pydantic）に入る場所で解析されます。関数ごとに 1 つの戻り値の形。`if name ==` のラダーではなくテーブルによるディスパッチ。協力者はミックスインではなくオブジェクト。テストがパッチするためだけに保持されるモジュール定数はありません。
- **内部移動のための再エクスポートシムはありません。** 内部パスは API ではありません。シンボルを移動するということは、同じ PR でそのドキュメントを修正することを意味します（`website/docs`、`skills/`、すべての `AGENTS.md` を検索）。

## どこにでも適用されるルール

- **防御的な雑然さを置かない:** 失敗し得ないコードの周りにラッパーや `try/except: pass` を置かない。誰も設定しないフラグを置かない。E2E の証明なしに配線されたデッドコードを置かない。コメントは WHY を保ち、WHAT を削る。
- **argv の部分文字列からプロセス同一性を推測しない。** `gateway.status.looks_like_gateway_command_line` / `hermes_cli.update_cmd._hermes_holder_subcommand` を使う（HX003）。
- **`~/.hermes` をハードコードしない:** パスには `get_hermes_home()`、テキストには `display_hermes_home()`（HX001）。`_get_profiles_root()` は意図的に HOME にアンカーされています。
- **1 つのプロセスが多くのプロファイルにサービスを提供します。** ターンの外で実行されるコード（起動プローブ、エビクション、ティッカー、遅延コールバック、RPC メソッド、スレッドホップ、子プロセス生成）は、所有プロファイルのスコープを明示的にバインドします。`os.environ`、モジュールグローバル、インポート時の値は起動プロファイルのものを保持するため、バインドされていない読み取りはサイレントなデフォルトプロファイルのリークです。バインドポイントと継ぎ目: `gateway/AGENTS.md` § プロファイルスコープ（HX002/HX004/HX005/HX012、PS-P05/P06）。
- **マシン事実と実行可能ファイルの検索は `hermes_platform` を通ります。**
- **依存関係は上限を持ちます**（`>=floor,<next_major`。git URL と Actions は SHA に固定）。`pyproject.toml` を編集した後は `hermes pm lock` を実行して `uv.lock` をコミットします。生の pip/uv で Hermes 環境を決して変更しない。
- **TypeScript（デスクトップ、TUI）:** スレッド化された状態よりも機能所有のナノストア、薄いルートルート、狭いフックと同一場所のアクションモジュール、props と共有形状には `interface`、条件ラダーよりもテーブル駆動のディスパッチ。デスクトップはルートを `src/app`、アトムを `src/store`、純粋なヘルパーを `src/lib` に保持します。
- **コア/プラグインの交差を追加しない:** コアは特定のバンドル済みプラグインを決してインポートせず、プラグインは公開されたプラグイン API（`hermes_cli/data/plugin_api.json`、`ctx`）のみを使います。既存の交差はベースライン化されています。`scripts/boundary_lint.py` は新しいものに対してテストスイート（`scripts/check` ではなく）を失敗させます。
- **新しい設定キーまたはスラッシュコマンドはドキュメントと一緒に出荷されます**（`tests/ci/test_docs_drift.py`）。
- **コミットと PR:** マージ前に `main` にリベースします（古いブランチからのスカッシュは新しい修正をサイレントに巻き戻します）。修正ごとに 1–2 個の不変条件テストを、ベースで赤であることを証明して。
- **テスト:** 常に `scripts/run_tests.sh`。裸の `pytest` は決して。挙動契約であり、変更検出器やソース読み取りテストは決して。ホスト固有の挙動はそのホストで `@pytest.mark.platforms(...)` を使ってテストし、`sys.platform` を偽装しては決して。テストは `~/.hermes/` に決して書き込みません。

## ルーティングテーブル

| エリア | 読む | カバー |
|---|---|---|
| `run_agent.py`、`agent/` | `agent/AGENTS.md` | ターンフェーズ、メッセージフロー不変条件、圧縮、モデル/aux 解決、i18n |
| `cli.py`、`hermes_cli/` | `hermes_cli/AGENTS.md` | CLI ミックスイン、スラッシュレジストリ、設定システム、スキン、`hermes update`、プロファイル / マルチプレックス |
| `gateway/` | `gateway/AGENTS.md` | アダプタ、メッセージガード、ストリーミング、通知、トークンロック、§ プロファイルスコープ |
| `plugins/platforms/` 新しいアダプタ | `gateway/platforms/ADDING_A_PLATFORM.md` | ステップバイステップのアダプタガイド |
| `tools/`、`toolsets.py`、`model_tools.py` | `tools/AGENTS.md` | ツール追加、レジストリ、ツールセット、委任、セッションスコープの表面ツール |
| `plugins/`、`hermes_cli/plugins*.py` | `plugins/AGENTS.md` | プラグインの種類、ネイティブ互換契約、ツリー内ポリシー、境界 lint |
| `plugin-catalog/` | `plugin-catalog/README.md` | カタログ受け入れルール（開発者ガイドにミラー。同一に保つ） |
| `tui_gateway/`、`ui-tui/` | `tui_gateway/AGENTS.md` | プロセスモデル、JSON-RPC トランスポート、スラッシュフロー |
| `web/`、`hermes_cli/web_routers/` | `web/AGENTS.md` | ダッシュボードは実際の TUI を埋め込む |
| `apps/desktop/` | `apps/desktop/AGENTS.md`、`apps/desktop/src/AGENTS.md` | 状態権威、ゲートウェイバックエンド契約、スラッシュパレット、Bot モード |
| `skills/`、`optional-skills/`、`agent/curator*.py` | `skills/AGENTS.md` | frontmatter、執筆基準、キュレーター |
| `cron/`、kanban | `cron/AGENTS.md` | スケジューラ不変条件、ジョブフィールド、kanban ディスパッチャ |
| `tests/` | `tests/AGENTS.md` | ランナー、配置、OS マーカー、`wine2e`、禁止されたテスト形状 |
| `pm/`、`pyproject.toml` | `pm/AGENTS.md` | ピン留めポリシー、PM 所有環境、リリース年齢ルール |
| `hermes_platform/` | `hermes_platform/AGENTS.md` | ホスト事実、リゾルバ |
| `acp_adapter/` | `website/docs/developer-guide/acp-internals.md` | エディタ用 ACP サーバー |
| `providers/` | `providers/README.md` | `ProviderProfile` レジストリと ABC |

PR ワークフロー: `CONTRIBUTING.md`（メンテナー向け: `hermes-agent-dev` スキル。ここには出荷されません）。