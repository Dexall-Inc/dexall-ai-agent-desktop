# skills/ と optional-skills/ の同梱スキル、作成基準、Curator

ルートの `AGENTS.md` に加えて適用する。詳細は `website/docs/developer-guide/creating-skills.md`、
ユーザー向け資料は `website/docs/user-guide/features/skills.md` と `curator.md` を参照する。

## スキルの配置先

- **`skills/`** は既定で読み込める組み込みスキル。カテゴリ別に配置する（`skills/github/`、`skills/mlops/` など）。
- **`optional-skills/`** は依存関係が重いスキルや用途が限定されるスキル。同梱されるが既定では有効にならない。
  `hermes skills install official/<category>/<skill>` で導入する（アダプターは `tools/skills_hub_official.py` の
  `OptionalSkillSource`）。カテゴリは `autonomous-ai-agents, blockchain, communication, creative,
  devops, email, health, mcp, migration, mlops, productivity, research, security, web-development`。

スキルの PR では配置先を確認する。依存関係が重いか用途が限定される場合は `optional-skills/` に置く。

## SKILL.md のフロントマター

`name`、`description`、`version`、`author`、`license`、`platforms`（OS の制約。`[macos]`、
`[linux, macos]` など）、`metadata.hermes.tags`、`metadata.hermes.category`、
`metadata.hermes.related_skills`、`metadata.hermes.config`（必要な config.yaml の設定。
`skills.config.<key>` に保存し、セットアップで入力を求め、読み込み時に渡す）。
トップレベルの `tags:` と `category:` も受け付ける。ローダーが `metadata.hermes.*` から値を反映する。

## 作成基準（`tests/skills/test_authoring_standards.py` で強制）

新規または改修したスキルは、同梱・オプション・外部コントリビューションを問わず、マージ前に以下を満たす。

1. **`description` は60文字以内の一文で、末尾にピリオドを付ける。** 長い説明は一覧を膨らませ、多数の
   スキルを読み込む際に重要な情報を見つけにくくする。提供する機能を述べ、実装の説明や宣伝文句
   （「強力」「包括的」「シームレス」「高度」など）は省く。スキル名やカテゴリ名も繰り返さない。
   一覧に表示する既定の幅は60文字（`SKILL_PROMPT_DESC_LIMIT`）。`skills.index_desc_limit` でユーザー自身の
   一覧と `skill_manage` の上限は広げられるが、この基準は変わらない。
2. **説明で参照する Hermes 標準ツールや依存先の MCP サーバーはバッククォートで囲む。**
   例は `terminal`、`web_extract`、`read_file`、`patch`、`search_files`、`vision_analyze`、
   `browser_exec`、`delegate_task`。エージェントに対応ツールがあるシェルコマンドは使い方の説明に出さない。
   `grep` は `search_files`、`cat`／`head`／`tail` は `read_file`、`sed`／`awk` は `patch`、
   `find`／`ls` は `search_files target='files'` を使う。MCP の依存先と設定は `## Prerequisites` に記載する。
   サードパーティの CLI やパイプラインはスクリプト内に置く。
<!-- no-tmp: ok — names the POSIX-only anti-pattern reviewers look for -->
3. **`platforms:` は実際のインポートや処理に照らして確認する。** POSIX 専用機能（固定の `/tmp`、
   `fcntl`、`termios`、`os.setsid`、`os.kill(pid, 0)`、`/proc`、`signal.SIGKILL`、bash のヒアドキュメント、
   `osascript`、`apt`、`systemctl`）にはプラットフォームの宣言が必要。まず `tempfile.gettempdir`、
   `pathlib.Path`、`psutil.pid_exists`、`grep` の代わりの Python フィルターなどで移植性を確保し、
   実際に OS に依存する場合に対応範囲を絞る。
4. **`author` には人間の作成者を先に記載する。** 外部コントリビューターの実名と GitHub ハンドルを先に、
   「Hermes Agent」を後に記載する。Hermes で作成してコミットの著者が「Hermes Agent」になった場合は、
   人間の作成者名に修正する。
5. **セクションの順序。** `# <Skill> Skill`、機能と対象外を示す2〜3文の導入、`## When to Use`、
   `## Prerequisites`、`## How to Run`、`## Quick Reference`、`## Procedure`、`## Pitfalls`、
   `## Verification`。複雑なスキルは約200行、単純なものは約100行を目安にする。冗長な導入、宣伝文句、
   前提条件ですでに説明した環境変数の再説明を削る。
6. **`scripts/`、`references/`、`templates/`。** パーサーや複雑なロジックを呼び出しのたびに
   モデルに書かせない。補助スクリプトを同梱し、スキルからの相対パスで参照する。
7. **テストは `tests/skills/test_<skill>_skill.py` に置く。** 標準ライブラリ、pytest、`unittest.mock`
   だけを使い、実ネットワークには接続しない。`scripts/run_tests.sh tests/skills/test_<skill>_skill.py -q` を実行する。
8. **`.env.example` への追加項目は明確に区切る。** コントリビューターのコピーは古いことが多い。
   取り込み時は、そのスキル専用ブロックの外にある変更を除外する。

スキル読み込みツールに `offset`／`limit` でページネーションを設けない。ルートの方針に従い、全文を読み込む。
外部スキル PR の取り込み・改修チェックリストは `hermes-agent-dev` スキルの
`references/new-skill-pr-salvage.md` を参照する。

## Curator（スキルのライフサイクル）

エージェントが作成したスキルの使用状況をバックグラウンドで追跡し、使われていないスキルを自動で
アーカイブする。保存先は `~/.hermes/skills/.archive/` で、復元できる。中核処理は
`agent/curator.py`（レビュー、状態の自動遷移、LLM 用のレビュープロンプト）と
`agent/curator_backup.py`（実行前の tar.gz スナップショット）。CLI は `hermes_cli/curator.py` の
`hermes curator status|run|pause|resume|pin|unpin|archive|restore|
prune|backup|rollback`。使用状況は `tools/skill_usage.py` が `~/.hermes/skills/.usage.json` に管理する
（`use_count`、`view_count`、`patch_count`、`last_activity_at`、`state` の active/stale/archived、`pinned`）。
設定は `curator:` の `enabled, interval_hours, min_idle_hours, stale_after_days,
archive_after_days, backup.*`。LLM の呼び出しは `auxiliary` を経由する（`agent/AGENTS.md`）。

自動処理の対象は `created_by: "agent"` のスキルに限る。同梱スキルとハブから導入したスキルは対象外。
`prune_builtins` を使うと、利用状況による決定的な処理で同梱スキルをアーカイブできる。
同梱スキルも、`skill_view` が読み込みを拒否する `skills.disabled` のスキルも、LLM のレビュー候補には
入れない。フォークに提示するのは、読み書きできるスキルだけにする。

自動処理で実行できるのはアーカイブまで。固定したスキルは自動遷移と LLM レビューの対象外。
`skill_manage(action="delete")` は固定したスキルの削除を拒否する。patch/edit/write_file/remove_file は引き続き使え、
エージェントによる改善を続けられる。
