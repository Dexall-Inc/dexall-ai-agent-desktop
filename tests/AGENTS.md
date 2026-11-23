# tests/ — Hermes のテストの書き方と実行方法

ルートの `AGENTS.md` に重ねて適用されます。テストを追加または変更する前に、必ずお読みください。

## テストの実行

**必ず `scripts/run_tests.sh` を使用してください**。素の `pytest` は絶対に使わないでください。CI との整合性を強制します。資格情報変数を未設定にし、`TZ=UTC`、`LANG=C.UTF-8`、`HERMES_HOME` を一時ディレクトリにし、`scripts/run_tests_parallel.py` によるファイル単位のサブプロセス分離（xdist なし。ワーカー数は CPU 数に応じてスケール）を行うため、モジュールレベルの dict や ContextVars がファイル間で漏れることはありません。大規模なマシンで API キーを設定したまま直接 `pytest` を実行すると、「ローカルでは動くのに CI では失敗する」という事態（およびその逆）が繰り返し発生しています。

チェックアウトでブートストラップされた Python を使ってテスト用インタープリタを準備します。

```bash
python -m pm.build_env --source . --out .venv --group dev --group test
```

これは新規ビルドであり、インプレース同期ではありません。使い捨ての出力が存在する場合は、そのプロセスを停止し、再生成する前に意図的に削除してください。ランナーは`PYTHONPATH`をクリアするため、PMシェルのアクティベーションだけではpytestは提供されません。チェックアウト外の新規出力には、`HERMES_PYTHON`をそのインタープリタに設定してください。

```bash
scripts/run_tests.sh                                    # full suite
scripts/run_tests.sh tests/gateway/                     # one directory
scripts/run_tests.sh tests/agent/test_foo.py -k test_x  # runner is file-granular; -k narrows
scripts/run_tests.sh -v --tb=long                       # pytest flags pass through
just test tests/agent/test_foo.py -k test_x             # same runner; refuses to start with no path
```

`just test-all` は明示的なフルスイート形式です。

- **Flake ポリシー:** 失敗した FILE は新しいサブプロセスで一度だけ再試行されます（`--file-retries`; `HERMES_TEST_FILE_RETRIES=0` で無効化）。シグナルまたはファイルタイムアウトで kill されたワーカーは再試行されません（暴走プロセスの再起動は被害を倍増させるため）。再試行での成功は green ですが、`⚠ FLAKY` の下で両方の出力とともに表示されます。これは修正すべきバグであり、ノイズではありません。タイミングテストは静かなランナーを前提にしてはいけません。ウォールクロックの制限は 2 秒以上、イベントベースの同期、`assert not _wait_until(...)` の競合なし。テスト内で新たに非ゼロの `time.sleep`/`asyncio.sleep` を出すとラチェット（HX013）が失敗します。Event を待つか、`tests.waiting.wait_until` / `async_wait_until` でポーリングしてください。
- **配置はソースツリーを反映します。** テストは `tests/<top-level source dir>/` に置きます（`tests/hermes_cli/`、`tests/agent/`、`tests/cron/`、`tests/gateway/relay/`、...）。インストーラー/アップデータのスクリプトテストは `tests/scripts/{install,desktop_update}/` の下に置きます。ルートレベルのモジュール（`batch_runner`、`utils`、`hermes_constants`、パッケージング）のテストのみが `tests/` に直接置かれます。ファイル名に issue 番号を含めないでください。issue はモジュールの docstring に記載します（`test_89315_x.py` → `test_x.py`、"Regression for #89315"）。
- **配置（CI レーン）:** `scripts/ci/classify_changes.py` は変更されたファイルによってジョブを選択します。`package.json`、`pnpm-lock.yaml`、`tsconfig.json`、または `.ts/.tsx/.js/
  .mjs/.cjs` のソースについて検証する Python テストは、JS のみの PR では実行されません（PR では green、分類器がフェイルオープンする `main` では red）。そのようなテストは `tests/*.py` ではなく vitest スイートに属します。
- **テストは `~/.hermes/` に書き込んではいけません。** `tests/conftest.py` の autouse の `_isolate_hermes_home` フィクスチャは `HERMES_HOME` をリダイレクトします。テストで `~/.hermes/` をハードコードしないでください。プロファイルテストは `Path.home()` もモックするため、`_get_profiles_root()` / `_get_default_hermes_home()` は一時ディレクトリに留まります（パターン: `tests/hermes_cli/test_profiles.py`）。
  ```python
  @pytest.fixture
  def profile_env(tmp_path, monkeypatch):
      home = tmp_path / ".hermes"; home.mkdir()
      monkeypatch.setattr(Path, "home", lambda: tmp_path)
      monkeypatch.setenv("HERMES_HOME", str(home))
      return home
  ```
  テストは `patch.object(Path, "home", ...)` で、`HERMES_HOME` も設定しなければならない。コードは `Path.home()/.hermes` ではなく環境変数を読むからだ。

- **テストは決してネットワークに到達しない。** `tests/conftest.py` は、このマシン外のホストへのあらゆるルックアップを pytest プロセス全体にわたって拒否する（アドレスリテラルとループバックは通る）。テストが必要とするものはフィクスチャから提供する。すなわち、`127.0.0.1` 上のサーバー、スタブ化したトランスポート、シード済みキャッシュ（models.dev、モデルカタログ）、または SSRF ガード用ルックアップのための `public_dns` だ。ネットワークを開くのは、シークレットで保護されたカナリア（`@pytest.mark.live`）と PM ツールチェーン／ホイールのダウンロード（`@pytest.mark.allow_network`）だけである。テストが起動する子プロセスはフェンスの外にある。シード済みのホームを与えること。

## ホスト OS を偽装しない

ホストごとに実際に異なる挙動は、そのホスト上で `@pytest.mark.platforms("linux")` / `platforms("macos")` / `platforms("windows")` を使ってテストする。`sys.platform` をパッチしてはならない。ホストに依存しないものはマークなしのままでよい。プラットフォームをデータとして受け取る純粋関数（`hidden_windows_child_options(opts,
is_windows=True)`）や、宣言・パッケージングの不変条件（「pyproject は `tzdata` を `sys_platform == 'win32'` マーカー付きで宣言している」）などだ。モジュールレベルの `IS_WINDOWS` フラグを設定して `windows_detach_flags()` を呼ぶのは偽装である。境界線はこうだ。**テストを通過させるためにインタープリタに別の OS 上にいると信じ込ませる必要があるなら、それはその OS 上で行うべきテストである。** 複数のプラットフォームを順にまたぐテストは分割される。Linux 上のホストネイティブの arm と、その他の arm はそれぞれ独自のマーク付きテストとして扱う。

1つのテストにつきマーカーは1つで、任意の数のspec文字列（any-ofセマンティクス）と、オプションのarchフィルタを指定できます。複数のOSでゲートするには、複数のspecを1つのマーカーに渡してください。1つのテストに`platforms()`デコレータを複数重ねることは決してしないでください（conftestはコレクション時にそれを拒否します）。

```python
@pytest.mark.platforms("linux", "macos")  # ONE marker, two specs: runs on either
def test_posix_signal_path(): ...
```

他の単一マーカー形式（それぞれが単独で完全なマーカーです）：
`platforms("windows")`（ネイティブWindowsのみ）、`platforms("not macos")`
（macOS以外の任意の場所）、`platforms("windows", arch="arm64")`（arm64上のネイティブWindows）、`platforms("posix")`（LinuxまたはmacOS）。

仕様：`linux`、`macos`、`windows`、`posix`、`any`、および`not <spec>`。
歴史的な`linux_only` / `macos_only` / `windows_only`マーカーは
完全に置き換えられました — `platforms`がツリー内で唯一のホストゲーティングマーカーです。

**実WindowsプロセストポロジーE2E：`wine2e`レーン。** モックでは再現できない実際のWindowsプロセス挙動に関する主張（venvホルダーのスキャン、プロセスツリーの親子関係、ランチャー/ワーカーの連鎖、デタッチのセマンティクス）については、オンデマンドのワークフロー`windows-venv-e2e.yml`があり、実際の`windows-latest`ランナー上で`tests/hermes_cli/test_venv_holder_windows_live.py`を実行します — 実際のプロセスを起動し、実際の検出コードを駆動します。psutilのモックはありません。これは`wine2e/**`ブランチへのプッシュ時のみ発火します（PRとmainでは不活性で、通常の作業ではコストはかかりません）。実証済みのワークフロー：正しい挙動を固定するプローブを書き、`wine2e/`ブランチにプッシュして未修正のコード上でバグをライブ再現し、修正を構築し、レーンがグリーンになるまで反復し、その後PRを開きます — 正確なヘッド上でのライブ証跡が、レビュアーが求めるWindowsの証明です。そのサブシステムに触れるときはライブスイートを拡張してください。直接の親ではなく、argvによって見つけられるゲートウェイのANCESTORに対してアサートしてください（venvシムにより、すべてのスポーンがランチャー/ワーカーの連鎖になります）。

**マーカーを使う。素の`skipif`は使わない。** `scripts/ci/list_os_marked_tests.py`は、`platforms(...)`内の引用されたスペックを解決することで、OSレーンがどのファイルをインポートするかを決定する（`"posix"`はmacOSレーンに到達し、`"not linux"`は他の両方に到達する）。そしてレーンは`-m platforms`で選択し、conftestのテストごとのホストスキップが実際のゲーティングを行う。したがって`@pytest.mark.skipif(sys.platform != "win32")`でゲートされたテストは、どのホストでも実行されない——それは、それを実行するはずのレーンには決してインポートされず、フルスイートのレーンはそれをスキップする。`skipif(sys.platform == "win32")`は`platforms("posix")`になる。非ホスト条件（`os.geteuid() == 0`）は、マーカーの隣に別の`skipif`として残る。スペックの綴り間違いはスキップではなくコレクションエラーになる。テスト自身がホストマーカーを持つファイルに、モジュールレベルの`pytestmark =
platforms(...)`を重ねてはいけない——conftestは2つの`platforms()`マーカーを持つテストをハードリジェクトする（すべてのホストでスキップされ、どこでもグリーンと報告されるテスト）。

同様に、`@parametrize`の非ホスト行をプラットフォーム横断で`pytest.skip()`してはいけない——OSごとに1つのマーク付きテストに分割するか、そうでなければホストの行だけが実行される。

## 変更検出テストを書かないこと

変更検出器は、*変更されるはずの*データが更新されるたびに失敗する。モデルカタログ、`_config_version`、列挙カウント、ハードコードされたモデルリストなどだ。カバレッジは増えず、日常的な更新のたびに負担を強いる。やってはいけないこと: `assert "gemini-2.5-pro" in _PROVIDER_MODELS["gemini"]`、`assert DEFAULT_CONFIG["_config_version"] == 21`、`assert len(models) == 8`。やるべきこと: `assert
"gemini" in _PROVIDER_MODELS and len(_PROVIDER_MODELS["gemini"]) >= 1`(配管が機能する)、`assert raw["_config_version"] == DEFAULT_CONFIG["_config_version"]`(マイグレーションが最新に到達する)、`assert not (set(moonshot_models) & coding_plan_only_models)`(リークがない)、すべてのカタログモデルにコンテキスト長のエントリがあること(関係性)。スナップショットのように読めるなら削除し、2つのデータ間の契約のように読めるなら残す。レビュアーは新しい変更検出器を却下し、著者は再レビューの前にそれらを変換する。

## テストでソースコードを読まない

`.py`/`.ts`/`.tsx`ファイルのテキストを読むテストは、*ソースの形状*をテストしているのであって、挙動ではない。完全に禁止だ。実装が微妙に壊れていても(正規表現が誤って配線された呼び出し箇所にマッチする)、合格してしまい、正しいリファクタリングでは失敗する。バンドル済み/ミニファイ済みのアーティファクトに対して実行できず、構造的なクリーンアップを妨げ、誤った自信を与える。`fs.readFileSync('main.ts')` + `assert.match(source, /spawn\(...hiddenWindowsChildOptions/)`をやってはいけない。ロジックを純粋な/DIテスト可能な関数に抽出して呼び出すこと:
```ts
export function hiddenWindowsChildOptions(options = {}, isWindows = process.platform === 'win32') {
  if (!isWindows || 'windowsHide' in options) return options
  return { ...options, windowsHide: true }
}
```
ロジックがgod-fileにインラインで存在し、抽出が破壊的に感じられるなら、それは正規表現で回避するのではなく、抽出すべきシグナルである。
