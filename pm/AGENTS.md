# pm/ — 依存関係と Hermes 環境

ルートの `AGENTS.md`（ピン留めルールの短縮版を記載）の上に適用される。

## 依存関係のピン留めポリシー

すべての依存関係は上限を付ける（litellm の侵害 #2796/#2810、Mini Shai-Hulud ワーム、2026年5月）。PyPI: `>=floor,<next_major`（`"httpx>=0.28.1,<1"`）。1.0 未満: `<0.(minor+2)`（`>=0.29,<0.32`）。Git URL: 40文字のコミット SHA。GitHub Actions: SHA + `# vN` コメント。CI 専用の Python 要件: `==exact`。素の `>=X.Y.Z` は CI とレビュアーに拒否される。

`pyproject.toml` を変更したら、`hermes pm lock` を実行し、`./activate` を再ソースし、`pyproject.toml` を `uv.lock` とともにコミットする。参照: #2810（上限）、#9801（SHA ピン留め + 監査 CI）。

PM は Hermes の Python 依存関係の変更を所有する。宣言されたランタイムの extra には `pm.sync_venv(['extra'], explicit=True)` を、セットアップ/同期には `hermes pm install` を、破損した依存関係には `hermes pm repair` を使う。生の pip や uv で Hermes 環境を変更してはならない。

開発者専用ツール（`just`）は `pm.testenv.DEVELOPER_TOOLS` 内の任意パッケージである。`--test-environment` インストールはロックファイルがピン留めするものをプロビジョニングする。ユーザーインストールやデスクトップバンドルは決してそれをしない。

新しいビルド出力には `pm.build_environment` を、隔離されたツール環境には `pm.ensure_environment` を使う。呼び出し側は uv ではなくインタープリタまたはツールパスを受け取る。

Nix の宣言的 uv2nix ビルドと無関係なユーザープロジェクトは、引き続き独立して所有される。

`[tool.uv] exclude-newer = "3 days"` の公開後の経過日数チェックは **Hermes 自身の依存関係のみ**を対象とし、完全一致ピンを含む。パッケージごとの免除クラスは1つだけ: CA トラストストア（`certifi`）。その失効リリースは出荷当日にロックへ到達しなければならない（`exclude-newer-package`。ここに他のものを置いてはならない）。これは Hermes がロックするとき（`hermes pm lock`、CI のロックチェック）に実行され、ユーザーのマシン上では決して実行されない。生成されたすべてのワークスペースはこのカットオフを落とす（`pm/workspace.py::_without_release_age`）。したがって、アップロード時刻のないミラーはインストールを壊さない（#135589）。プラグイン解決はこれによって変更されない。コアの完全一致ピンはそのまま維持され、プラグインはコアの宣言された範囲内で推移的なコアパッケージを移動できる（`tests/pm/test_workspace_build_inputs.py::test_plugin_can_move_compatible_transitive_but_not_exact_requirement`）。プラグインの `python_dependencies` はプラグイン自身のポリシーに従う。Teknium の裁定: 「プラグインは我々の14日ルールに従う必要はない……Hermes 自身の依存関係だけが従う必要がある」。日付はユーザーではなく我々が確認する。ピン留めする依存関係は、公開から3日を超えている必要がある。

JS: `pnpm-workspace.yaml` 内の `minimumReleaseAge`（14日）。免除は `minimumReleaseAgeExclude` 内の1つの完全一致 `- name@1.2.3  # why` 行であり、`hermes pm update --pnpm` がそれを指名し、後で削除する（`website/docs/reference/package-management.md` § リリース年齢とパッケージミラー）。
