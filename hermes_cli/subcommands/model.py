"""``hermes model`` subcommand parser."""

from __future__ import annotations

from typing import Callable


def build_model_parser(subparsers, *, cmd_model: Callable) -> None:
    """Attach the ``model`` subcommand to ``subparsers``."""
    model_parser = subparsers.add_parser(
        "model", help="既定のモデルとプロバイダーを選ぶ",
        description="対話形式で推論プロバイダーと既定のモデルを選びます。")
    model_parser.add_argument(
        "--refresh", action="store_true",
        help="モデル選択画面のディスクキャッシュを消去し、各プロバイダーの /v1/models から一覧を再取得します。")
    model_parser.add_argument(
        "--portal-url", help="Nous ログインに使う Portal のベース URL（既定: 本番環境）")
    model_parser.add_argument(
        "--inference-url",
        help="Nous ログインに使う推論 API のベース URL（既定: 本番環境）")
    model_parser.add_argument(
        "--client-id", default=None,
        help="Nous ログインに使う OAuth クライアント ID（既定: hermes-cli）")
    model_parser.add_argument("--scope", default=None, help="Nous ログイン時に要求する OAuth スコープ")
    model_parser.add_argument(
        "--no-browser", action="store_true",
        help="Nous ログイン時にブラウザーを自動で開かない")
    model_parser.add_argument(
        "--timeout", type=float, default=15.0,
        help="Nous ログイン時の HTTP リクエストのタイムアウト（秒、既定: 15）")
    model_parser.add_argument(
        "--ca-bundle", help="Nous の TLS 検証に使う CA バンドル（PEM）のパス")
    model_parser.add_argument(
        "--insecure", action="store_true",
        help="Nous ログイン時の TLS 検証を無効にする（テスト専用）")
    model_parser.set_defaults(func=cmd_model)
