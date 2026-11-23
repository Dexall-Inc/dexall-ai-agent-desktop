"""``hermes update`` subcommand parser."""

from __future__ import annotations

from typing import Callable


def build_update_parser(subparsers, *, cmd_update: Callable) -> None:
    """Attach the ``update`` subcommand to ``subparsers``."""
    from hermes_cli.release_channels import validate_name
    update_parser = subparsers.add_parser(
        "update", help="ALL AI5.2 TACT を更新する",
        description="Git から変更を取得し、依存関係を再インストールします。")
    update_parser.add_argument(
        "--gateway", action="store_true", default=False,
        help="ゲートウェイモード。標準入力の代わりにファイルベースの IPC で確認します（/update の内部用）。",
    )
    update_parser.add_argument(
        "--check", action="store_true", default=False,
        help="インストールせずに更新の有無を確認します。")
    update_parser.add_argument(
        "--plan", action="store_true", default=False,
        help="更新計画を表示して終了します。インストール方式（git/docker/nix）、全プロファイルの稼働中サービス、その監視プロセス、稼働中のコードのバージョン、再起動方法が表示されます。変更は加えません。")
    update_parser.add_argument(
        "--list-venv-holders", action="store_true", default=False,
        help="Windows で venv を使用中のプロセスを JSON 配列 [{pid, exe, argv, kind}] で表示して終了します。使用中のプロセスがなければ 0、あれば 3 を返します。読み取り専用です。kind は gateway / backend（Desktop serve）/ hermes:<subcommand> / python です。Windows 以外では [] を返します。")
    update_parser.add_argument(
        "--no-backup", action="store_true", default=False,
        help="今回の更新前バックアップをすべて省略します。簡易スナップショットと完全な ZIP が対象です。updates.pre_update_backup より優先されます。",
    )
    update_parser.add_argument(
        "--backup", action="store_true", default=False,
        help="updates.pre_update_backup の設定にかかわらず、簡易スナップショットと HERMES_HOME の ZIP を作成します。",
    )
    update_parser.add_argument(
        "--yes", "-y", action="store_true", default=False,
        help="確認待ちを省略します。設定の移行と stash の復元を承認し、upstream リモートの追加と API キーの入力は省略します。キーの入力は hermes config migrate で行えます。",
    )
    update_parser.add_argument(
        "--keep-stash", action="store_true", default=False,
        help="ローカル変更は更新前に stash に退避し、更新後も stash に残します。Desktop のアップデーターがローカルの編集を自動で適用しないために使います。")
    update_parser.add_argument(
        "--branch", default=None, metavar="NAME",
        help="指定したブランチから更新します。Dexall の既定の更新先は develop です。現在のブランチが異なる場合は、未コミットの変更を自動で stash してから切り替えます。")
    update_parser.add_argument(
        "--switch-branch", action="store_true", default=False,
        help="updates.parked_branch_strategy が update_in_place の場合に限り、今回は更新先ブランチへ切り替えて更新します。作業ブランチの履歴は維持されます。既定の switch では動作は変わりません。作業ツリーに変更がある場合は実行を拒否します。")
    update_parser.add_argument(
        "--force", action="store_true", default=False,
        help="Linux/macOS では処理中のターンを中断し、この更新が管理するゲートウェイと子プロセスを停止してから更新し、再起動します。約12秒で停止しないプロセスは強制終了します。既に待機中の更新には適用できません。Windows では別の hermes.exe があっても続行し、処理の終了は待ちます。venv の使用チェックは --force-venv で指定します。",
    )
    update_parser.add_argument(
        "--force-venv", action="store_true", default=False,
        help="Windows で Desktop バックエンド、ゲートウェイ、ターミナルなどが venv を使用中でも変更を試みます。.pyd がロックされていると更新に失敗する場合があるため、検出が誤りと確認できた場合に使用してください。",
    )
    update_parser.add_argument(
        "--set-channel",
        default=None,
        type=validate_name,
        metavar="CHANNEL",
        help=(
            "このインストールの更新チャンネルを config.yaml の update.installs に保存します。チャンネル名はリリースアーカイブで解決します。公式ソース版は既定で stable（公開済みの最新 vX.Y.Z のコミット）を参照します。main はソースブランチを追跡し、Dexall では develop を参照します。パッケージ版はパッケージの識別情報で決まります。"
        ),
    )
    update_parser.add_argument(
        "--install-id",
        action="store_true",
        default=False,
        help=(
            "このインストールの ID とパスを表示して終了します。ID は config.yaml のチャンネル設定を識別します。"
        ),
    )
    update_parser.add_argument(
        "--channel",
        default=None,
        type=validate_name,
        metavar="CHANNEL",
        help=(
            "今回だけ CHANNEL を使用します。保存するには --set-channel を使います。stable と canary は公開リリース、main は最新のブランチのコミットを参照します。ソース版専用です。"
        ),
    )
    update_parser.add_argument(
        "--no-gateway-restart", action="store_true", default=False,
        help="コードと依存関係を更新し、ゲートウェイの再起動は後回しにします。ゲートウェイの cgroup 内で更新し、その後に別途再起動する場合に使います。",
    )
    update_parser.set_defaults(func=cmd_update)
