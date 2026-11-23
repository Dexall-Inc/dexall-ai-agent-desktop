"""``hermes gateway`` and ``hermes proxy`` subcommand parsers."""

from __future__ import annotations

import argparse
from typing import Callable

from hermes_cli.subcommands._shared import add_accept_hooks_flag


# `start`/`restart` on a named profile refuse while the default multiplexer serves it (a second gateway
# would double-bind its platforms); `gateway run` carries its own broader --force text.
_FORCE_SERVED_PROFILE_HELP = (
    "Start a separate gateway for this profile even when the default multiplexer already serves it "
    "(not recommended: two pollers on one bot token, port conflicts)")

# `stop`/`restart` ask before interrupting live turns, cron jobs or background delegations.
_INTERRUPT_HELP = (
    "{verb} without asking even while sessions are live (turns, cron jobs, background delegations): "
    "they are interrupted. Without it the command names the live work and asks y/N (refuses when "
    "there is no terminal). --interrupt is the same flag")


class _GatewayCommandParser(argparse.ArgumentParser):
    """``ensure``'s and ``attach``'s parser errors share their machine-readable command boundary."""

    def __init__(self, *args, json_verb=None, **kwargs):
        self.json_verb = json_verb
        super().__init__(*args, **kwargs)

    def parse_known_args(self, args=None, namespace=None):
        parsed, unknown = super().parse_known_args(args, namespace)
        if self.json_verb and unknown:
            self.error("unknown arguments")
        return parsed, unknown

    def error(self, message):
        if not self.json_verb:
            return super().error(message)
        print('{"endpoint":null,"reason_code":"invalid_invocation","state":"inaccessible"}')
        self.exit(2, f"gateway {self.json_verb}: invalid invocation\n")


def _flag(parser, *names, help, **kw):
    parser.add_argument(*names, action="store_true", help=help, **kw)


def _add_compat_platform_flag(parser: argparse.ArgumentParser) -> None:
    """Accept stale `gateway <verb> --platform X` docs without advertising it.

    Lifecycle commands operate on the gateway process, not one adapter; Photon briefly
    printed a per-platform start command during setup, so keep it parseable.
    """
    parser.add_argument("--platform", dest="platform", help=argparse.SUPPRESS)


def _add_system_flag(parser: argparse.ArgumentParser) -> None:
    _flag(parser, "--system", help="Linuxシステムレベルのゲートウェイサービスを対象にする")


def build_gateway_parser(
    subparsers, *, cmd_gateway: Callable, cmd_proxy: Callable, cmd_gateway_enroll: Callable
) -> None:
    """Attach the ``gateway`` and ``proxy`` subcommands to ``subparsers``."""
    gateway_parser = subparsers.add_parser("gateway", help="メッセージングゲートウェイの管理",
        description="メッセージングゲートウェイ（Telegram、Discord、WhatsApp、Weixinなど）を管理する")
    gateway_subparsers = gateway_parser.add_subparsers(
        dest="gateway_command", parser_class=_GatewayCommandParser)

    gateway_run = gateway_subparsers.add_parser(
        "run", help="ゲートウェイをフォアグラウンドで実行する（WSLとDockerに推奨）"
    )
    gateway_run.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="stderrログの詳細度を上げる（-v=INFO、-vv=DEBUG）",
    )
    gateway_run.add_argument(
        "-q", "--quiet", action="store_true", help="すべてのstderrログ出力を抑制する"
    )
    gateway_run.add_argument(
        "--replace",
        action="store_true",
        help="既存のゲートウェイインスタンスを置き換える（systemdに便利）",
    )
    gateway_run.add_argument(
        "--force",
        action="store_true",
        help=(
            "systemd/launchd/s6サービスがすでにこのプロファイルを監視している場合でも、フォアグラウンドゲートウェイを起動する。--forceがない場合、2番目のディスパッチャがサービスから逃げ出して共有ゲートウェイ状態を破損する可能性があるため、コマンドは拒否される。"
        ),
    )
    gateway_run.add_argument(
        "--no-supervise",
        action="store_true",
        help=(
            "s6-overlay Dockerイメージ内では、通常`gateway run`は監視対象のs6サービスに自動的にリダイレクトされる（これにより、ゲートウェイはクラッシュ時に自動再起動され、HERMES_DASHBOARDが設定されている場合は監視対象のダッシュボードも得られる）。--no-superviseを渡すとオプトアウトし、従来のpre-s6フォアグラウンド動作（ゲートウェイがコンテナのメインプロセスとなり、コンテナはゲートウェイの終了コードで終了する）を取得できる。s6コンテナ外では効果がない。"),
    )
    _flag(gateway_run, "--external-supervisor",
        help="外部のプロセスマネージャがこのフォアグラウンドゲートウェイを所有していることを宣言する。チャット内の再起動と更新は、切り離された置換プロセスを起動する代わりに、そのマネージャに戻って終了する。launchd/systemdラッパーがネイティブの環境マーカーを除去する場合に使用する。")
    # Internal: set only by a client that auto-starts its own gateway (chat, TUI, cron/kanban
    # clients). Never in service units, Desktop's `gateway ensure` start or a hand-run gateway.
    _flag(gateway_run, "--idle-exit", help=argparse.SUPPRESS)
    add_accept_hooks_flag(gateway_run)
    add_accept_hooks_flag(gateway_parser)

    from hermes_cli.gateway_runtime_cli import cmd_gateway_attach, cmd_gateway_ensure
    gateway_ensure = gateway_subparsers.add_parser(
        "ensure", json_verb="ensure",
        help="ローカルランタイムを、サービスをインストールまたは置き換えることなく確保する",
        epilog="Exit codes: 0 ready; 2 invalid invocation; 3 incompatible; "
               "4 authorization/profile mismatch; 5 deadline; 6 draining/update-paused; "
               "7 inaccessible/conflicting supervisor. Pending startup is not readiness.")
    _flag(gateway_ensure, "--json", help="資格情報を含まないJSON結果を1つ出力する（デフォルト）")
    gateway_ensure.add_argument("--timeout", default="60",
                                help="起動の合計デッドライン（秒）（デフォルト: 60）")
    gateway_ensure.set_defaults(func=cmd_gateway_ensure)

    gateway_attach = gateway_subparsers.add_parser(
        "attach", json_verb="attach",
        help="ローカルクライアントを接続する：ゲートウェイのWebSocket URLと一回限りのセッションチケット",
        description="このプロファイルにサービスを提供するゲートウェイのWebSocket URLと、それに対する一回限りのセッションチケットを出力します。これは、自身で/api/wsに接続するローカルクライアント用です。チケットは資格情報です：呼び出し元プロセスにのみ出力され、決してログに記録されず、発行から30秒後に失効します。",
        epilog="Exit codes: 0 attached; 2 invalid invocation; otherwise the exit code "
               "`hermes gateway ensure` gives the same verdict.")
    _flag(gateway_attach, "--json", help="1件のJSON結果を出力（デフォルト）")
    attach_mode = gateway_attach.add_mutually_exclusive_group()
    _flag(attach_mode, "--start", help="このプロファイルを提供するゲートウェイがない場合にゲートウェイを起動")
    _flag(attach_mode, "--recover",
        help="最初に検出し、ゲートウェイが準備できていない場合のみ（または古いHermesのゲートウェイを置き換えて）起動")
    gateway_attach.add_argument("--timeout", default="60",
                                help="--start/--recoverの起動デッドライン（秒）（デフォルト: 60）")
    gateway_attach.set_defaults(func=cmd_gateway_attach)

    from hermes_cli.gateway_runtime_tickets import cmd_gateway_tickets
    gateway_tickets = gateway_subparsers.add_parser(
        "tickets",
        help="SSH経由でゲートウェイに到達するクライアントに対して、使い捨てのHTTPおよびWebSocketチケットを発行",
        description="ゲートウェイのループバックポートを転送するクライアント（たとえばSSH経由）向けで、そのHTTP APIを呼び出します。--probeはこのホストが発行できるものを表示し、ゲートウェイには触れません。--serveは実行中のゲートウェイのエンドポイントを含むhello行を出力し、その後、stdinの各行{\"id\": ..., \"purpose\": \"native-http\"}に対して、使い捨てチケットを保持する1つのstdout行で応答し、stdinが閉じるまで続けます。行には、同じゲートウェイが提供する別のプロファイル用に \"profile\": \"<name>\" を追加できます。目的 \"interactive\" は、そのゲートウェイが提供するすべてのプロファイルに対するWebSocketのチケットです。ゲートウェイを起動することはありません。それには`hermes gateway attach --start`を使用してください。チケットは資格情報です。呼び出し元のプロセスにのみ出力され、決してログに記録されません。",
        epilog="Exit codes: 0 probe printed, or --serve ended at stdin EOF; 2 invalid invocation; "
               "otherwise (--serve with no gateway to use) the exit code `hermes gateway ensure` "
               "gives the same verdict.")
    _flag(gateway_tickets, "--json", help="JSON行を出力（デフォルト）")
    tickets_mode = gateway_tickets.add_mutually_exclusive_group(required=True)
    _flag(tickets_mode, "--probe", help="プロトコルバージョンとチケットの目的を表示し、何も起動しない")
    _flag(tickets_mode, "--serve", help="stdin上のチケット要求に、閉じられるまで応答する")
    gateway_tickets.set_defaults(func=cmd_gateway_tickets)

    gateway_start = gateway_subparsers.add_parser(
        "start", help="インストール済みのsystemd/launchdバックグラウンドサービスを起動する")
    _add_system_flag(gateway_start)
    _flag(gateway_start, "--all",
        help="起動前に、すべてのプロファイルにわたる古いゲートウェイプロセスをすべて強制終了します")
    _flag(gateway_start, "--force", help=_FORCE_SERVED_PROFILE_HELP)
    _add_compat_platform_flag(gateway_start)

    gateway_stop = gateway_subparsers.add_parser("stop", help="ゲートウェイサービスを停止します")
    _add_system_flag(gateway_stop)
    _flag(gateway_stop, "--all", help="すべてのプロファイルにわたるすべてのゲートウェイプロセスを停止します")
    _flag(gateway_stop, "-y", "--yes", "--interrupt", dest="interrupt", help=_INTERRUPT_HELP.format(verb="stop"))

    gateway_restart = gateway_subparsers.add_parser("restart", help="ゲートウェイサービスを再起動します")
    _add_system_flag(gateway_restart)
    _flag(gateway_restart, "--all",
        help="再起動前に、すべてのプロファイルにわたるすべてのゲートウェイプロセスを強制終了します")
    _flag(gateway_restart, "--force", help=_FORCE_SERVED_PROFILE_HELP)
    _flag(gateway_restart, "-y", "--yes", "--interrupt", dest="interrupt", help=_INTERRUPT_HELP.format(verb="restart"))
    _flag(gateway_restart, "--detach", help=(
        "インストール済みのサービスがない場合、このターミナルではなくバックグラウンドで置き換えを開始します（`gateway ensure` と同様）。再起動を短命なクライアントとして実行するアプリで使用されます"))
    _add_compat_platform_flag(gateway_restart)

    gateway_status = gateway_subparsers.add_parser("status", help="ゲートウェイのステータスを表示")
    _flag(gateway_status, "--deep", help="詳細なステータスチェック")
    _flag(gateway_status, "-l", "--full",
        help="サポートされている場合、完全な、切り詰められていないサービス/ログ出力を表示")
    _add_system_flag(gateway_status)
    _add_compat_platform_flag(gateway_status)

    # gateway install
    gateway_install = gateway_subparsers.add_parser(
        "install", help="ゲートウェイを systemd/launchd バックグラウンドサービスとしてインストール")
    _flag(gateway_install, "--force",
        help="強制再インストールし、デフォルトのマルチプレクサがすでにこのプロファイルを提供している場合でもインストールする")
    _flag(gateway_install, "--system",
        help="Linuxシステムレベルのサービスとしてインストールする（起動時に開始）")
    gateway_install.add_argument("--run-as-user", dest="run_as_user",
        help="Linuxシステムサービスが実行するユーザーアカウント")
    _flag(gateway_install, "--start-now", dest="start_now", default=None,
        help="インストール直後にゲートウェイサービスを開始する")
    gateway_install.add_argument("--no-start-now", dest="start_now", action="store_false",
        help="インストール後にゲートウェイサービスを開始しない")
    _flag(gateway_install, "--start-on-login", dest="start_on_login", default=None,
        help="ログイン/起動時にサービスが自動的に開始されるように有効にする")
    gateway_install.add_argument("--no-start-on-login", dest="start_on_login", action="store_false",
        help="ログイン/起動時にサービスが開始されないようにする")
    _flag(gateway_install, "--if-missing", dest="if_missing",
        help="ゲートウェイサービスが既にインストールされている場合は何もしない")
    _flag(gateway_install, "--force-unit-path", dest="force_unit_path",
        help="別のHERMES_HOMEを固定しているサービス定義をこのHERMES_HOMEに向け直す")
    _flag(gateway_install, "--elevated-handoff", dest="elevated_handoff", help=argparse.SUPPRESS)

    gateway_uninstall = gateway_subparsers.add_parser("uninstall", help="ゲートウェイサービスをアンインストールする")
    _add_system_flag(gateway_uninstall)

    gateway_subparsers.add_parser("list", help="すべてのプロファイルとそのゲートウェイステータスを一覧表示")

    gateway_subparsers.add_parser("setup", help="メッセージングプラットフォームを設定")

    gateway_migrate_legacy = gateway_subparsers.add_parser(
        "migrate-legacy", help="リネーム前のインストールから残っているレガシー hermes.service ユニットを削除",
        description="古いインストールから残っているレガシー Hermes ゲートウェイユニットファイル（例: hermes.service）を停止、無効化、削除します。プロファイルユニット（hermes-gateway-<profile>.service）および無関係なサードパーティサービスには一切触れません。")
    _flag(gateway_migrate_legacy, "--dry-run", dest="dry_run",
        help="削除せずに削除対象を一覧表示")
    _flag(gateway_migrate_legacy, "-y", "--yes", dest="yes", help="確認プロンプトをスキップする")

    gateway_migrate = gateway_subparsers.add_parser(
        "migrate", help="各プロファイルのゲートウェイを単一のホストゲートウェイに収束させる",
        description="このホストを1ホスト1ゲートウェイモデルに収束させる：各セカンダリプロファイルのゲートウェイとそのスーパーバイザーユニット（systemd、launchd、Windows Scheduled Task）を停止してアンインストールし、その後デフォルトプロファイルのゲートウェイを再起動してすべてのプロファイルにサービスを提供する。最初にプリフライトを実行する（重複するボットトークン、/p/<profile>/ イングレスを持たないポートバインディングプラットフォーム）が、ブロックされた場合は何も変更しない。再実行しても安全：半分移行されたホストは次回の実行で収束する。プロファイルごとのゲートウェイはもはやサポートされるトポロジではないため、ロールバックコマンドは存在しない。")
    _flag(gateway_migrate, "--multiplex", dest="multiplex", help="単一のホストゲートウェイに収束する（デフォルト）")
    _flag(gateway_migrate, "--dry-run", dest="dry_run", help="何も変更せずにプランとブロッカーを表示する")
    _flag(gateway_migrate, "-y", "--yes", dest="yes", help="確認なしで適用する")
    _flag(gateway_migrate, "--backends", dest="backends",
        help="serve/dashboard のバックグラウンドサービスとその所有権を報告する。サービスは変更しない（通常の Hermes 起動時の簿記処理は引き続き実行される）")
    _flag(gateway_migrate, "--json", dest="json",
        help="--backends を指定した場合: 機械可読な出力（レポート、プラン、実行結果、--status）")
    _flag(gateway_migrate, "--apply", dest="apply",
        help="--backends を指定した場合: このホームを古い dashboard/serve バックエンドから、同じアドレス上のゲートウェイの Webapp に移行する（--dry-run を指定した場合: プランとブロッカーのみを出力する）")
    _flag(gateway_migrate, "--restore", dest="restore",
        help="--backends を指定した場合: 完了済みのバックエンド移行をそのマニフェストから元に戻す")
    _flag(gateway_migrate, "--status", dest="status",
        help="--backends 付き: 最後または進行中のバックエンド移行の状態")
    gateway_migrate.add_argument("--address", dest="address", metavar="HOST:PORT",
        help="--backends --apply 付き: このアドレス上の古いバックエンド（複数見つかった: 他のものはまだブロック中）")
    _flag(gateway_migrate, "--keep-webapp-address", dest="keep_webapp_address",
        help="--backends --apply 付き: 古いバックエンドを退役させるが、Webapp は現在のアドレスに維持する")
    _flag(gateway_migrate, "--force-interrupt", dest="force_interrupt",
        help="--backends --apply 付き: 古いバックエンドでターンが実行中でも続行する（そのターンは中断される）")
    gateway_migrate.add_argument("--expect", dest="expect", metavar="TOKEN",
        help="--backends --apply 付き: 今見つかったバックエンドが、--dry-run --json プランが出力した expect_token を持つものでない限り、何も変更しない（終了コード 8）")
    _flag(gateway_migrate, "--detach", dest="detach",
        help="--backendsまたは--apply、または--restoreを指定した場合: このプロセスグループ/システムdのcgroupの外で実行し、即座に戻ります(その後--statusを実行してください)")
    _flag(gateway_migrate, "--detached-run", dest="detached_run", help=argparse.SUPPRESS)
    gateway_migrate.add_argument("--detached-ack", dest="detached_ack", help=argparse.SUPPRESS)

    # enroll: redeem a single-use connector token for the per-gateway secret + per-tenant
    # delivery key, written to .env. See website/docs/developer-guide/relay-connector-contract.md. EXPERIMENTAL.
    gateway_enroll = gateway_subparsers.add_parser("enroll",
        help="このゲートウェイをリレーコネクタに登録します(.envにリレー認証情報を書き込みます)",
        description="リレーコネクタで一度限りの登録トークンを使用します。Nous Portalアカウントとして認証され(コネクタがそこから権限のあるテナントを導出します)、このゲートウェイのゲートウェイごとのシークレットとテナントごとの配信キーを発行し、GATEWAY_RELAY_ID / GATEWAY_RELAY_SECRET / GATEWAY_RELAY_DELIVERY_KEYを~/.hermes/.envに書き込みます。ログインしている必要があります(hermes setup)。マネージドインストールでは利用できません。")
    gateway_enroll.add_argument("--token", default=None,
        help="コネクタからの一度限りの登録トークン(ゲートウェイ設定とともに配信されます)。GATEWAY_RELAY_ENROLL_TOKENでも設定できます。")
    gateway_enroll.add_argument("--connector-url", dest="connector_url", default=None,
        help="コネクタのベース/リレーURL。例: wss://connector.example.com/relay または https://connector.example.com.。GATEWAY_RELAY_URL / config.yamlのgateway.relay_urlでも設定できます。")
    gateway_enroll.add_argument("--gateway-id", dest="gateway_id", default=None,
        help="このゲートウェイインスタンスの安定したID（キルスイッチの粒度）。デフォルトは gw-<hostname>。")
    gateway_enroll.add_argument("--wake-url", dest="wake_url", default=None,
        help="Phase 5 §5.2 ウェイクURL：バッファリングされた作業がアイドル/サスペンド中に到着した際、このゲートウェイをウェイクするためにコネクタがポークする（ペイロードなしのGET）到達可能なURL。これによりゲートウェイは再接続してドレインします。~/.hermes/.env に GATEWAY_RELAY_WAKE_URL として永続化され、プロビジョニング時に転送されます。任意 — これがなくても、ゲートウェイは次回自ら再接続する際にドレインします。")
    gateway_enroll.set_defaults(func=cmd_gateway_enroll)

    # proxy: local OpenAI-compatible proxy attaching the user's OAuth provider credentials,
    # so external apps (Open WebUI, Karakeep, ...) ride a logged-in subscription.
    proxy_parser = subparsers.add_parser(
        "proxy", help="OAuthプロバイダーへのローカルOpenAI互換プロキシ",
        description="OpenAI互換リクエストをOAuth認証済みプロバイダー（例：Nous Portal）に転送するローカルHTTPサーバーを実行します。外部アプリは任意のベアラートークンでプロキシを指定できます。プロキシがあなたの実際の認証情報を添付します。")
    proxy_subparsers = proxy_parser.add_subparsers(dest="proxy_command")

    proxy_start = proxy_subparsers.add_parser("start", help="プロキシをフォアグラウンドで実行")
    proxy_start.add_argument("--provider", default="nous",
        help="上流プロバイダー: nous または xai (デフォルト: nous)。`hermes proxy providers` を参照。")
    proxy_start.add_argument("--host", default=None,
        help="バインドアドレス (デフォルト: 127.0.0.1)。LAN に公開するには 0.0.0.0 を使用。")
    proxy_start.add_argument("--port", type=int, default=None, help="バインドポート (デフォルト: 8645)")

    proxy_subparsers.add_parser("status", help="どのプロキシ上流が準備完了かを表示")
    proxy_subparsers.add_parser("providers", help="利用可能なプロキシ上流プロバイダーを一覧表示")
    proxy_parser.set_defaults(func=cmd_proxy)
    gateway_parser.set_defaults(func=cmd_gateway)
