"""``hermes doctor`` subcommand parser."""

from __future__ import annotations

from typing import Callable


def build_doctor_parser(subparsers, *, cmd_doctor: Callable) -> None:
    """Attach the ``doctor`` subcommand to ``subparsers``."""
    doctor_parser = subparsers.add_parser(
        "doctor", help="設定と依存関係を確認する",
        description="ALL AI5.2 TACT の設定や依存関係の問題を診断します。")
    doctor_parser.add_argument(
        "--fix", action="store_true", help="問題の自動修復を試みます。")
    doctor_parser.add_argument(
        "--live", action="store_true",
        help="静的チェックの後、設定済みの各ツールバックエンド（Firecrawl/FAL/browser/MCP/TTS/STT）に読み取り専用の確認リクエストを1回ずつ送ります。ネットワーク通信が発生します。")
    doctor_parser.add_argument(
        "--ack", metavar="ADVISORY_ID", default=None,
        help="ID を指定してセキュリティ勧告を確認済みにします。以降はその勧告が起動時に表示されません。有効な勧告と ID は hermes doctor で確認できます。")
    doctor_parser.set_defaults(func=cmd_doctor)
