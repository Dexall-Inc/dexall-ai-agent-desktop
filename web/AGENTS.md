# web/ + hermes_cli/web_routers/ のダッシュボード（`hermes dashboard` → `/chat`）

ルートの `AGENTS.md` に加えて、以下の方針を適用する。バックエンドのルーターは画面ごとに
`hermes_cli/web_routers/*.py` に分け、`hermes_cli/web_server.py` と関連する `web_server_*.py` から
登録する。フロントエンドは `web/src/` にある。Desktop と共通の JSON-RPC/WS クライアントは
`apps/shared`（`@hermes/shared`）にある。

## ダッシュボードは実際の `hermes --tui` を埋め込む

`hermes_cli/pty_bridge.py` と `web_server.py` の `@app.websocket("/api/pty")` が接続を担う。

- `web/src/pages/ChatPage.tsx` は xterm.js の `Terminal` をマウントする。描画には WebGL を使い、
  コンテナーのサイズ変更には `@xterm/addon-fit`、全角文字の幅には `@xterm/addon-unicode11` を使う。
- `/api/pty?token=…` は WebSocket にアップグレードする。認証には REST と同じ一時的な
  `_SESSION_TOKEN` を使う。ブラウザーはアップグレード時に `Authorization` を設定できないため、
  トークンはクエリパラメーターで渡す。
- サーバーは `ptyprocess` を通じて `hermes --tui` と同じプロセスを起動する。POSIX PTY が必要なため、
  WSL では動作する。Windows ネイティブでは動作しない。
- フレームは双方向とも PTY の生バイト列。サイズ変更は `\x1b[RESIZE:<cols>;<rows>]` で伝え、
  サーバーが受け取り `TIOCSWINSZ` で適用する。

**主要なチャット機能を React で再実装しない。** 会話履歴、入力欄と入力処理（スラッシュコマンドの
動作を含む）、PTY ターミナルは埋め込み TUI が担当する。Ink への追加はダッシュボードにも反映される。
会話履歴や入力欄の変更は Ink で行う（`tui_gateway/AGENTS.md`）。

**TUI を補助する構造化された React UI は追加できる。** サイドバーのウィジェット、インスペクター、
要約、状態パネル（`ChatSidebar`、`ModelPickerDialog`、`ToolCall`）が該当する。補助 UI の状態は
PTY 子プロセスのセッションから独立させ、エラーを表示した後もターミナルを使い続けられるようにする。

## `dashboard` と `serve`

`dashboard` と `serve` は `cmd_dashboard` と `start_server` を共有する独立した機能であり、
相互に起動しない。Desktop はヘッドレスバックエンドの `serve` を起動する（`headless_backend=True`）。
このとき `cmd_dashboard` は `_build_web_ui` を省略し、`HERMES_SERVE_HEADLESS=1` を設定する。
そのため、`web_dist/` が残っていても `mount_spa()` が SPA を無効にし、JSON-RPC、WebSocket、API
だけが利用可能になる。Desktop のビルドと実行はこのフロントエンドに依存しない。
詳細は `apps/desktop/src/AGENTS.md` を参照。

各機能（`serve`、`dashboard`、`webapp`）で許可される処理は `hermes_cli/web_server_surface.py` の
表にまとめている。`ui_surface` の文字列を比較する代わりに、この表を参照する。

## ルール

- 認証は新しい REST ルートと WebSocket エンドポイントでも同じセッショントークンを使う。
- ルーターは機能ごとに1ファイルに分ける。機能を追加する場合は `web_routers/<surface>.py` を新設し、
  `web_server.py` に処理を増やさない。
- Python テストは `tests/hermes_cli/`（ルーター、PTY ブリッジ）、JavaScript テストは `web/` の
  Vitest スイートに置く。ルートのテスト方針に従い、Python テストでは `package.json` や `.tsx` の
  ソース内容を検証しない。ルートの TypeScript スタイルルールも適用する。
