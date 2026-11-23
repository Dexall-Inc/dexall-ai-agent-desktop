"""``hermes config`` subcommand parser."""

from __future__ import annotations

from typing import Callable

from hermes_cli.subcommands._shared import add_json_flag


def build_config_parser(subparsers, *, cmd_config: Callable) -> None:
    """Attach the ``config`` subcommand to ``subparsers``."""
    config_parser = subparsers.add_parser(
        "config", help="設定を表示・編集する",
        description="ALL AI5.2 TACT の設定を管理します。")
    config_subparsers = config_parser.add_subparsers(dest="config_command")

    config_subparsers.add_parser("show", help="現在の設定を表示します。")
    config_subparsers.add_parser("edit", help="エディターで設定ファイルを開きます。")

    config_get = config_subparsers.add_parser("get", help="有効な設定値を表示します。")
    config_get.add_argument("key", nargs="?", help="設定キー（例: model）")
    add_json_flag(config_get, "値を JSON で表示します。")
    config_get.add_argument(
        "--raw", action="store_true",
        help="認証情報をマスクせずに表示します。既定では api_key、token、secret などの値を隠します。")

    config_set = config_subparsers.add_parser("set", help="設定値を指定します。")
    config_set.add_argument(
        "key", nargs="?", help="設定キー（例: model、terminal.backend）")
    config_set.add_argument("value", nargs="?", help="設定する値")
    config_set.add_argument(
        "--force", action="store_true",
        help="実行中のバージョンが認識しないキーを書き込みます。通常、既知のセクション内の未知のパスは拒否され、未知のトップレベルキーは通知付きで書き込まれます。")

    config_unset = config_subparsers.add_parser("unset", help="設定値を削除します。")
    config_unset.add_argument("key", nargs="?", help="削除する設定キー")

    config_subparsers.add_parser("path", help="設定ファイルのパスを表示します。")
    config_subparsers.add_parser("env-path", help=".env ファイルのパスを表示します。")
    config_subparsers.add_parser("check", help="不足している設定や古い設定を確認します。")
    config_subparsers.add_parser("migrate", help="新しい設定項目を追加します。")

    config_parser.set_defaults(func=cmd_config)
