"""``hermes status`` subcommand parser."""

from __future__ import annotations

from typing import Callable


def build_status_parser(subparsers, *, cmd_status: Callable) -> None:
    """Attach the ``status`` subcommand to ``subparsers``."""
    status_parser = subparsers.add_parser(
        "status", help="各コンポーネントの状態を表示する",
        description="ALL AI5.2 TACT の各コンポーネントの状態を表示します。")
    status_parser.add_argument(
        "--full", "--all", dest="full", action="store_true",
        help="簡潔な概要に代えてすべてのセクションを表示します。キーは伏せられます。")
    status_parser.add_argument(
        "--deep", action="store_true", help="詳細なチェックを実行します。--full を含み、時間がかかる場合があります。")
    status_parser.set_defaults(func=cmd_status)
