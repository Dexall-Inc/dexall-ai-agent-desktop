"""``hermes profile`` subcommand parser."""

from __future__ import annotations

from typing import Callable


def build_profile_parser(subparsers, *, cmd_profile: Callable) -> None:
    """Attach the ``profile`` subcommand to ``subparsers``."""
    profile_parser = subparsers.add_parser(
        "profile", help="プロファイルを管理 — 複数の分離されたHermesインスタンス")
    profile_subparsers = profile_parser.add_subparsers(dest="profile_action")

    profile_subparsers.add_parser("list", help="すべてのプロファイルを一覧表示")
    profile_use = profile_subparsers.add_parser("use", help="スティッキーなデフォルトプロファイルを設定")
    profile_use.add_argument("profile_name", help="プロファイル名（または 'default'）")

    profile_create = profile_subparsers.add_parser("create", help="新しいプロファイルを作成")
    profile_create.add_argument("profile_name", help="プロファイル名（小文字、英数字）")
    profile_create.add_argument(
        "--clone", action="store_true",
        help="アクティブなプロファイルから config.yaml、.env、SOUL.md、スキルをコピーします（メッセージングボットのトークン/許可リストは残されます。--clone-channels を参照）")
    profile_create.add_argument(
        "--clone-all", action="store_true",
        help="アクティブなプロファイルの完全コピー（すべての状態。プロファイルごとの履歴とメッセージングチャンネルを除く）")
    profile_create.add_argument(
        "--clone-from", metavar="SOURCE",
        help="コピー元のプロファイル。--clone を意味します。--clone-all が設定されている場合を除く")
    profile_create.add_argument(
        "--clone-channels", action="store_true",
        help="コピー元のメッセージングチャンネル（ボットトークン、許可リスト、プラットフォームセクション）もコピーします。1つのボットトークンを保持する2つのプロファイルは衝突します。コピー元がライブの多重化ゲートウェイによって提供されている場合は拒否されます。")
    profile_create.add_argument(
        "--sync-imports", action="store_true",
        help="--clone/--clone-fromを使用する場合：新しいプロフィールが同じClaude Code / Codexツリーに対して登録されたままになるよう、`hermes import-agent`同期マニフェストも引き継ぎます（`hermes -p <name> import-agent --sync`）。ソースプロフィールから設定を同期することはありません。")
    profile_create.add_argument(
        "--no-alias", action="store_true", help="ラッパースクリプトの作成をスキップ")
    profile_create.add_argument(
        "--isolated-auth", action="store_true",
        help="デフォルトプロフィールのものを共有する代わりに、ログイン（auth.json）を一度だけコピーします。デスクトップボットページで「キーとアカウントを共有」のチェックを外すのと同じです。単回使用のOAuthログインはコピーから除外され、引き続きデフォルトプロフィールから読み取られます。名前付きプロフィールからは、そのログインは常にこの方法でコピーされます。")
    profile_create.add_argument(
        "--no-credentials", action="store_true",
        help="起動プロフィールからAPIキー、ログイン、モデルをコピーしません（後で`<name> setup`を実行してください。ソースのキーをコピーする--clone*とは併用できません）。デフォルトプロフィールのログインは、新しいプロフィールがサインインしていない任意のプロバイダーに対して読み取り可能なままです。")
    profile_create.add_argument(
        "--no-skills", action="store_true",
        help="バンドルされたスキルを含まない空のプロフィールを作成します（`hermes update`スキル同期をオプトアウト）",
    )
    profile_create.add_argument(
        "--description", default=None,
        help="このプロフィールが何に優れているかの1〜2文の説明。カンバン分解ツールがプロフィール名だけでなく役割に基づいてタスクを振り分けるために使用されます。スキップして後で`hermes profile describe`で追加できます。")

    profile_delete = profile_subparsers.add_parser("delete", help="プロフィールを削除")
    profile_delete.add_argument("profile_name", help="削除するプロフィール")
    profile_delete.add_argument("-y", "--yes", action="store_true", help="確認プロンプトをスキップ")

    profile_describe = profile_subparsers.add_parser(
        "describe", help="プロフィールの説明を読み取るか設定します（カンバンオーケストレーターが使用）")
    profile_describe.add_argument(
        "profile_name", nargs="?", default=None,
        help="説明するプロファイル（省略すると --all --auto を使用してスイープ）")
    profile_describe.add_argument(
        "--text", default=None,
        help="説明をこの正確なテキストに設定します（既存の説明を上書き）")
    profile_describe.add_argument(
        "--auto", action="store_true",
        help="補助LLMを介して説明を自動生成します（auxiliary.profile_describer を使用）")
    profile_describe.add_argument(
        "--overwrite", action="store_true",
        help="--auto と併用すると、ユーザー作成の説明も置き換えます（デフォルト：欠落している説明または以前に自動生成された説明のみを埋める）")
    profile_describe.add_argument(
        "--all", dest="all_missing", action="store_true",
        help="--auto と併用すると、説明がないすべてのプロファイルに対して実行します")

    profile_show = profile_subparsers.add_parser("show", help="プロフィールの詳細を表示")
    profile_show.add_argument("profile_name", help="表示するプロフィール")

    profile_alias = profile_subparsers.add_parser("alias", help="ラッパースクリプトを管理")
    profile_alias.add_argument("profile_name", help="プロフィール名")
    profile_alias.add_argument("--remove", action="store_true", help="ラッパースクリプトを削除")
    profile_alias.add_argument(
        "--name", dest="alias_name", metavar="NAME",
        help="カスタムエイリアス名（デフォルト：プロファイル名）")

    profile_rename = profile_subparsers.add_parser(
        "rename", help="プロファイルの名前を変更（'default'：表示名を設定。IDは変更されません）")
    profile_rename.add_argument("old_name", help="現在のプロファイル名")
    profile_rename.add_argument(
        "new_name",
        help="新しいプロファイル名（'default'の場合：表示名 — 正規のIDは'default'のまま）")

    profile_purge = profile_subparsers.add_parser(
        "purge-identity",
        help="削除されたプロファイルのセッション/ルーティングIDのパージを再試行",
        description="`hermes profile delete` が自動的に実行するセッション/ルーティング ID のパージを再実行します。これが必要になる時点ではプロファイルディレクトリは既に削除されています。削除されたプロファイル名でキー付けされたままの状態（ルーティングキー、ハートビート、ルーティング/配信行）が削除されます。ゲートウェイを再起動した後（DB からルーティングインデックスを再読み込みします）、または停止した後に実行してください。冪等です。")
    profile_purge.add_argument("profile_name", help="削除されたプロファイル名")

    profile_migrate = profile_subparsers.add_parser(
        "migrate-identity",
        help="名前が変更されたプロファイルのセッション/ルーティング ID マイグレーションを再試行",
        description="`hermes profile rename` が自動的に実行するセッション/ルーティング ID マイグレーションを再実行します。これが必要になる時点では名前変更は既に完了しているため、旧名と新名を渡してください。旧プロファイル名でキー付けされたままの状態（セッションキー、profile_name、ハートビート、ルーティング/配信行）が新しい名前に再キー付けされます。ゲートウェイを再起動した後（DB からルーティングインデックスを再読み込みします）、または停止した後に実行してください。冪等です。")
    profile_migrate.add_argument("old_name", help="名前変更前のプロファイル名")
    profile_migrate.add_argument("new_name", help="リネーム後のプロファイル名")

    profile_export = profile_subparsers.add_parser("export", help="プロファイルをアーカイブにエクスポート")
    profile_export.add_argument("profile_name", help="エクスポートするプロファイル")
    profile_export.add_argument(
        "-o", "--output", default=None,
        help="出力ファイル（デフォルト: デフォルトのHermesホーム配下の管理されたprofile-exports/<name>-<timestamp>.tar.gz）")

    profile_import = profile_subparsers.add_parser("import", help="アーカイブからプロファイルをインポート")
    profile_import.add_argument("archive", help=".tar.gz アーカイブへのパス")
    profile_import.add_argument(
        "--name", dest="import_name", metavar="NAME",
        help="プロファイル名（デフォルト: アーカイブから推測）")

    # ---------- Distribution subcommands (issue #20456) ----------
    profile_install = profile_subparsers.add_parser(
        "install", help="git URL またはローカルディレクトリからプロファイルディストリビューションをインストール",
        description="Hermes プロファイルディストリビューションをインストールします。SOURCE には git URL（github.com/user/repo、https://..., git@...）またはルートに distribution.yaml を含むローカルディレクトリを指定できます。")
    profile_install.add_argument("source", help="ディストリビューションソース（git URL またはローカルディレクトリ）")
    profile_install.add_argument(
        "--name", dest="install_name", metavar="NAME",
        help="プロファイル名を上書き（デフォルト: マニフェストから読み取り）")
    profile_install.add_argument(
        "--alias", action="store_true",
        help="インストールされたプロファイル用のシェルラッパーエイリアスを作成")
    profile_install.add_argument(
        "--force", action="store_true",
        help="同名の既存プロファイルを上書き（ユーザーデータは保持）")
    profile_install.add_argument(
        "-y", "--yes", action="store_true", help="マニフェストプレビューの確認をスキップ")

    profile_update = profile_subparsers.add_parser(
        "update", help="ディストリビューションを再取得して更新を適用（ユーザーデータは保持）",
        description="記録されたソースからディストリビューションを取得し、ディストリビューションが所有するファイル（SOUL.md、mcp.json）と、ディストリビューションに同梱されているスキルおよびcronジョブを上書きします。自分で追加したスキルやcronジョブはそのまま残ります。ユーザーデータ（メモリ、セッション、認証情報、.env）には一切触れません。config.yamlは--force-configが渡されない限り保持されます。")
    profile_update.add_argument("profile_name", help="更新するプロファイル")
    profile_update.add_argument(
        "--force-config", action="store_true",
        help="config.yamlも上書きします（通常はユーザーの上書き設定を保持するために保存されます）")
    profile_update.add_argument("-y", "--yes", action="store_true", help="確認をスキップ")

    profile_info = profile_subparsers.add_parser(
        "info", help="プロファイルのディストリビューションマニフェスト（バージョン、要件、ソース）を表示します")
    profile_info.add_argument("profile_name", help="検査するプロファイル")

    profile_parser.set_defaults(func=cmd_profile)
