"""``hermes skills`` subcommand parser."""

from __future__ import annotations

from typing import Callable

from hermes_cli.subcommands._shared import add_json_flag, add_yes_flag


def _flag(parser, *names, help, **kw):
    parser.add_argument(*names, action="store_true", help=help, **kw)


# Registry sources, then provider filters (GitHub taps stored under source="github").
_SOURCE_CHOICES = [
    "all", "official", "skills-sh", "well-known", "github", "clawhub", "lobehub", "browse-sh",
    "nvidia", "openai", "anthropic", "huggingface", "voltagent", "gstack", "minimax"]


def build_skills_parser(subparsers, *, cmd_skills: Callable) -> None:
    """Attach the ``skills`` subcommand to ``subparsers``."""
    skills_parser = subparsers.add_parser(
        "skills", help="スキルの検索、インストール、設定、管理",
        description="skills.sh、よく知られたエージェントスキルエンドポイント、GitHub、ClawHub、その他のレジストリからスキルを検索、インストール、検査、監査、設定、管理します。",
    )
    skills_subparsers = skills_parser.add_subparsers(dest="skills_action")

    skills_trust = skills_subparsers.add_parser("trust",
        help="プロジェクトを信頼し、そのリポジトリローカルのスキル（./.hermes/skills、./.agents/skills）を読み込む")
    skills_trust.add_argument("path", nargs="?", default=None,
        help="信頼するプロジェクトルート（デフォルト: cwd を囲む git チェックアウト）")

    skills_untrust = skills_subparsers.add_parser(
        "untrust", help="リポジトリのプロジェクトスキル信頼を撤回する")
    skills_untrust.add_argument("path", nargs="?", default=None,
        help="信頼しないプロジェクトルート（デフォルト: cwd を囲む git チェックアウト）")

    skills_browse = skills_subparsers.add_parser(
        "browse", help="利用可能なすべてのスキルを閲覧（ページング対応）")
    skills_browse.add_argument("--page", type=int, default=1, help="ページ番号（デフォルト: 1）")
    skills_browse.add_argument(
        "--size", type=int, default=20, help="1ページあたりの結果数（デフォルト: 20）")
    skills_browse.add_argument("--source", default="all", choices=_SOURCE_CHOICES,
        help="ソースまたはプロバイダーでフィルタリング（例: nvidia、openai）（デフォルト: すべて）")

    skills_search = skills_subparsers.add_parser("search", help="スキルレジストリを検索")
    skills_search.add_argument("query", help="検索クエリ")
    skills_search.add_argument("--source", default="all", choices=_SOURCE_CHOICES,
        help="ソースまたはプロバイダでフィルタ（例: nvidia, openai）")
    skills_search.add_argument("--limit", type=int, default=25, help="最大結果数")
    add_json_flag(
        skills_search, "テーブルの代わりにJSONを出力（完全な識別子、スクリプト向け）")

    skills_install = skills_subparsers.add_parser("install", help="スキルをインストール")
    skills_install.add_argument("identifier",
        help="スキル識別子（例: openai/skills/skill-creator）またはSKILL.mdファイルへの直接のHTTP(S) URL",
    )
    skills_install.add_argument("--category", default="", help="インストール先のカテゴリフォルダ")
    skills_install.add_argument("--name", default="",
        help="スキル名を上書きする（SKILL.mdに`name:`フロントマターがないURLからインストールする場合に便利）",
    )
    _flag(skills_install, "--force", help="ブロックされたスキャン判定にもかかわらずインストールする")
    add_yes_flag(skills_install, "確認プロンプトをスキップ（TUIモードで必要）")

    skills_inspect = skills_subparsers.add_parser(
        "inspect", help="スキルをインストールせずにプレビュー")
    skills_inspect.add_argument("identifier", help="スキル識別子")

    skills_list = skills_subparsers.add_parser("list", help="インストール済みスキルを一覧表示")
    skills_list.add_argument("--source", default="all", choices=["all", "hub", "builtin", "local"])
    _flag(skills_list, "--enabled-only",
        help="無効なスキルを非表示。`-p <profile>` と併用すると、そのプロファイルで実際に読み込まれるスキルを正確に確認できます。")

    skills_check = skills_subparsers.add_parser(
        "check", help="インストール済みのハブスキルを更新がないか確認する")
    skills_check.add_argument("name", nargs="?", help="確認する特定のスキル（デフォルト: すべて）")

    skills_update = skills_subparsers.add_parser("update", help="インストール済みのハブスキルを更新する")
    skills_update.add_argument(
        "name", nargs="?", help="更新する特定のスキル（デフォルト: すべての古いスキル）")
    _flag(skills_update, "--force",
        help="ローカルで編集したスキルを上書きする（デフォルトではスキップされます）")

    skills_audit = skills_subparsers.add_parser("audit", help="インストール済みハブスキルを再スキャン")
    skills_audit.add_argument("name", nargs="?", help="監査する特定のスキル（デフォルト: すべて）")
    _flag(skills_audit, "--deep", help="Pythonファイルに対してASTレベルの解析を実行（オプトイン診断）")

    skills_uninstall = skills_subparsers.add_parser(
        "uninstall", help="ハブにインストールされたスキルを削除")
    skills_uninstall.add_argument("name", help="削除するスキル名")
    add_yes_flag(skills_uninstall)

    skills_reset = skills_subparsers.add_parser("reset",
        help="バンドルされたスキルをリセット — 「ユーザー変更」トラッキングをクリアして、更新が再び機能するようにします",
        description="バンドルされたスキルのエントリを同期マニフェスト（~/.hermes/skills/.bundled_manifest）からクリアし、今後の「hermes update」実行時にユーザー変更としてマークされないようにします。--restoreを渡すと、現在のコピーをバンドル版に置き換えることもできます。")
    skills_reset.add_argument("name", help="リセットするスキル名（例: google-workspace）")
    _flag(skills_reset, "--restore",
        help="現在のコピーも削除し、バンドル版を再コピーします")
    add_yes_flag(skills_reset, "--restore使用時に確認プロンプトをスキップします")

    skills_list_modified = skills_subparsers.add_parser(
        "list-modified", help="編集済みのバンドルスキルを一覧表示します（`hermes update`が保持しているもの）",
        description="ローカルコピーが最後に同期されたバージョンと異なるバンドルスキル、つまり`hermes update`がユーザー変更として報告してスキップするものを表示します。変更を確認するには`hermes skills diff <name>`を、更新を再開するには`hermes skills reset <name>`を使用してください。")
    add_json_flag(skills_list_modified, "リストをJSONとして出力します")

    skills_diff = skills_subparsers.add_parser(
        "diff", help="バンドルスキルの自分のコピーが標準バージョンとどのように異なるかを表示します",
        description="バンドルスキルのローカルコピーと現在のバンドル（標準）バージョンとの間の統一差分を出力し、`hermes skills reset`を実行する前に何が変更されたかを確認できるようにします。")
    skills_diff.add_argument("name", help="スキル名（例：google-workspace）")

    skills_opt_out = skills_subparsers.add_parser(
        "opt-out", help="バンドルされたスキルがこのプロファイルにシードされるのを停止する",
        description="インストーラー、`hermes update`、および直接同期がバンドルされたスキルをアクティブなプロファイルにシードするのを停止するように、.no-bundled-skills マーカーを書き込みます。デフォルトでは、ディスク上の既存のものには何も触れません。--remove を渡すと、未変更のバンドルされたスキルも削除されます（ユーザー編集済みおよびハブ/ローカルのスキルは決して削除されません）。")
    _flag(skills_opt_out, "--remove", help="既に存在する未変更のバンドルされたスキルも削除する")
    add_yes_flag(skills_opt_out, "--remove を使用する際に確認プロンプトをスキップする")

    skills_opt_in = skills_subparsers.add_parser(
        "opt-in", help="バンドルスキルのシードを再度有効にする（オプトアウトを元に戻す）",
        description=".no-bundled-skills マーカーを削除して、次の `hermes update` でバンドルスキルが再度シードされるようにします。今すぐ再シードするには --sync を渡します。")
    _flag(skills_opt_in, "--sync",
        help="更新を待たずにバンドルスキルをすぐに再シードする")

    skills_repair_official = skills_subparsers.add_parser(
        "repair-official", help="リポジトリのソースから公式のオプションスキルをバックフィルまたは復元する",
        description="公式オプションスキルの出所を修復します。デフォルトでは、完全一致したものについてのみハブのメタデータをバックフィルします。--restore を渡すと、optional-skills/ から欠落または変更されたアクティブなコピーを置き換え、既存のコピーを先に復元バックアップへ移動します。すべてのオプションスキルを修復するには名前 'all' を使用します。")
    skills_repair_official.add_argument(
        "name", help="公式のオプションスキルフォルダ/フロントマター名、または 'all'")
    _flag(skills_repair_official, "--restore",
        help="公式のオプションソースから復元し、既存の一致するコピーをバックアップする")
    add_yes_flag(skills_repair_official, "--restore使用時に確認プロンプトをスキップする")

    skills_publish = skills_subparsers.add_parser("publish", help="スキルをレジストリに公開する")
    skills_publish.add_argument("skill_path", help="スキルディレクトリへのパス")
    skills_publish.add_argument(
        "--to", default="github", choices=["github", "clawhub"], help="ターゲットレジストリ")
    skills_publish.add_argument(
        "--repo", default="", help="ターゲットGitHubリポジトリ（例: openai/skills）")

    skills_snapshot = skills_subparsers.add_parser(
        "snapshot", help="スキル設定のエクスポート/インポート")
    snapshot_subparsers = skills_snapshot.add_subparsers(dest="snapshot_action")
    snap_export = snapshot_subparsers.add_parser("export", help="インストール済みスキルをファイルにエクスポート")
    snap_export.add_argument("output", help="出力JSONファイルパス（stdoutには - を使用）")
    snap_import = snapshot_subparsers.add_parser(
        "import", help="ファイルからスキルをインポートしてインストールする")
    snap_import.add_argument("input", help="入力JSONファイルパス")
    _flag(snap_import, "--force", help="注意判定にもかかわらず強制インストールする")

    skills_tap = skills_subparsers.add_parser("tap", help="スキルソースを管理する")
    tap_subparsers = skills_tap.add_subparsers(dest="tap_action")
    tap_subparsers.add_parser("list", help="設定済みタップを一覧表示する")
    tap_add = tap_subparsers.add_parser("add", help="GitHubリポジトリをスキルソースとして追加")
    tap_add.add_argument("repo", help="GitHubリポジトリ（例: owner/repo）")
    tap_rm = tap_subparsers.add_parser("remove", help="タップを削除")
    tap_rm.add_argument("name", help="削除するタップ名")

    # config sub-action: interactive enable/disable
    skills_subparsers.add_parser(
        "config", help="対話型スキル設定 — 個別スキルの有効化/無効化")

    skills_parser.set_defaults(func=cmd_skills)
