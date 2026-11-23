"""``hermes logs`` subcommand parser."""

from __future__ import annotations

import argparse
from typing import Callable


def build_logs_parser(subparsers, *, cmd_logs: Callable) -> None:
    """Attach the ``logs`` subcommand to ``subparsers``."""
    logs_parser = subparsers.add_parser(
        "logs",
        help="Hermes のログを表示・絞り込みする",
        description="agent.log、errors.log、gateway.log、gui.log、desktop.log、update.log、desktop-update-handoff.log を表示・追跡・絞り込みします。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
使用例:
    hermes logs                    agent.log の末尾50行を表示
    hermes logs -f                 agent.log をリアルタイムで追跡
    hermes logs errors             errors.log の末尾50行を表示
    hermes logs gateway -n 100     gateway.log の末尾100行を表示
    hermes logs gui -f             gui.log をリアルタイムで追跡
    hermes logs desktop -f         desktop.log（Electron の起動・バックエンド）を追跡
    hermes logs update             update.log（hermes update の出力）の末尾50行を表示
    hermes logs handoff            desktop-update-handoff.log の末尾50行を表示
    hermes logs --level WARNING    WARNING 以上を表示
    hermes logs --session abc123   セッション ID で絞り込む
    hermes logs --component tools  ツール関連の行だけ表示
    hermes logs --since 1h         直近1時間の行を表示
    hermes logs --since 30m -f     30分前から現在まで表示し、以後も追跡
    hermes logs list               利用できるログファイルとサイズを一覧表示
""")
    logs_parser.add_argument(
        "log_name",
        nargs="?",
        default="agent",
        help="表示するログ。agent（既定）、errors、gateway、gui、desktop、update、handoff。list はファイル一覧を表示。",
    )
    logs_parser.add_argument(
        "-n", "--lines", type=int, default=50, help="表示する行数（既定: 50）")
    logs_parser.add_argument(
        "-f", "--follow", action="store_true", help="ログをリアルタイムで追跡（tail -f と同様）")
    logs_parser.add_argument(
        "--level", metavar="LEVEL", help="表示する最低ログレベル（DEBUG、INFO、WARNING、ERROR）")
    logs_parser.add_argument(
        "--session", metavar="ID", help="指定文字列を含むセッション ID の行に絞り込む")
    logs_parser.add_argument(
        "--since", metavar="TIME", help="TIME 前からの行を表示（例: 1h、30m、2d）")
    logs_parser.add_argument(
        "--component", metavar="NAME",
        help="コンポーネントで絞り込む（gateway、agent、tools、cli、cron、gui）")
    logs_parser.set_defaults(func=cmd_logs)
