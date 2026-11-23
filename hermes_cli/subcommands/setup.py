"""``hermes setup`` subcommand parser."""

from __future__ import annotations

from typing import Callable


def build_setup_parser(subparsers, *, cmd_setup: Callable) -> None:
    """Attach the ``setup`` subcommand to ``subparsers``."""
    setup_parser = subparsers.add_parser(
        "setup", help="対話式セットアップ",
        description="ウィザードで ALL AI5.2 TACT を設定します。項目を指定するには hermes setup model|tts|terminal|gateway|tools|telemetry|agent を実行します。")
    setup_parser.add_argument(
        "section", nargs="?",
        choices=["model", "tts", "terminal", "gateway", "tools", "telemetry", "agent"],
        default=None, help="ウィザード全体の代わりに指定した項目だけを設定します。")
    setup_parser.add_argument(
        "--non-interactive", action="store_true",
        help="対話なしで実行します。既定値と環境変数を使います。")
    setup_parser.add_argument(
        "--reset", action="store_true", help="設定を既定値に戻します。")
    setup_parser.add_argument(
        "--reconfigure", action="store_true",
        help="既存インストールでは現在の値を初期値としてウィザード全体を再実行します。引数なしの hermes setup と同じ動作で、互換性のために残されています。")
    setup_parser.add_argument(
        "--quick", action="store_true",
        help="既存インストールで未設定の項目だけを確認します。")
    setup_parser.add_argument(
        "--portal", action="store_true",
        help="OAuth で Nous Portal にログインし、Nous のモデルと推論プロバイダーを設定して Tool Gateway を有効にします。ウィザードの残りは省略します。")
    setup_parser.set_defaults(func=cmd_setup)
