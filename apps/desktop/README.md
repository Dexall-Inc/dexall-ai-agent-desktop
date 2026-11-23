# Dexall ALL AI5.2 TACT Desktop

TACT のネイティブデスクトップアプリです。Nous Research の Hermes Desktop をベースに、Dexall がこのフォークの `develop` ブランチで保守しています。

- CLI とゲートウェイと同じエージェント、設定、スキル、メモリを利用できます。
- ストリーミング応答とツール実行結果、ファイルやWebページの並列プレビュー、音声入力をサポートします。
- Desktop の既定言語は日本語です。保存済みの言語設定があれば、その言語で表示します。
- 設定画面から API プロバイダーとモデルを選べます。

## インストールと起動

[ルートのクイックインストール](../../README.md#クイックインストール)から TACT のランタイムをセットアップし、次を実行します。

```sh
hermes desktop
```

既存のランタイムが見つからない場合は、オンボーディングからローカルに導入するか、既存のゲートウェイに接続できます。

## 更新

ソース版は git の `origin` を参照します。このフォークから導入した場合の更新先は [Dexall の `develop`](https://github.com/Dexall-Inc/dexall-ai-agent-desktop/tree/develop) です。配布パッケージの公開状況は [GitHub Releases](https://github.com/Dexall-Inc/dexall-ai-agent-desktop/releases) を確認してください。

配布版の更新は macOS では Electron Updater、Windows のサイドロード版では App Installer、Store 版では Microsoft Store が処理します。パッケージのビルドと署名の詳細は [BUILDING.md](BUILDING.md) を参照してください。

## Screenshot shortcut (macOS)

Enable **Settings → Keyboard Shortcuts → Screenshot shortcut**, then press the
left and right Command keys together in any app. Hermes captures that app's
frontmost window and attaches the image to the last-active Hermes composer,
including split-pane chats. It does not send the draft or capture the whole
screen. Release both keys before taking another screenshot.

The shortcut is off by default and saved only on this Mac. macOS requires
**Input Monitoring** and **Screen & System Audio Recording** permission; the
settings row links to the relevant system pane and offers Retry. If macOS asks
to restart the app after granting access, do so before retrying. Review the
attachment before sending, especially when the captured window is sensitive.

## Requirements

Bundled packages provide Python 3.14 and their supported dependencies.
Source/bootstrap builds have a separate preparation path. Platform-native
requirements, including system Git on POSIX, are described in [BUILDING.md](BUILDING.md).
macOS source builds also require Xcode Command Line Tools to compile the native
shortcut helper. Prebuilt installers include it; no compiler is needed at runtime.

---

## Development

Want to hack on the app itself? Install workspace deps from the repo root once, then run the dev server from this directory:

```bash
pnpm install         # from repo root — links apps/desktop, web, apps/shared
cd apps/desktop
pnpm run dev         # Vite renderer + Electron, which boots the Python backend
```

`just desktop` runs the same dev server from the repository root.

On Windows x64, the first `pnpm run dev` (and `profile:main`) fetches `get-windows`' native binding into `node_modules`, because the dependency install skips its script; if that fails or takes over two minutes, dev starts without `read_window_below` and retries next time. That fetch reads a mirror or proxy only from the environment (`npm_config_node_get_windows_binary_host_mirror`, `HTTP_PROXY` or `npm_config_proxy`), not from `.npmrc`.

Point the app at a specific source checkout, or sandbox it away from your real config:

```bash
# throwaway HERMES_HOME, separate Electron userData, distinct app name to avoid the single-instance lock
../../scripts/dev-sandbox.sh pnpm run dev
HERMES_DESKTOP_HERMES_ROOT=/path/to/clone pnpm run dev
HERMES_HOME=$HOME/.hermes/cache/scratch/throwaway pnpm run dev
pnpm run dev:fake-boot   # exercise the startup overlay with deterministic delays
```

### Building installers

```bash
pnpm run dist:mac     # DMG + zip
pnpm run dist:win     # MSIX
pnpm run dist:linux   # AppImage + deb + rpm
pnpm run pack         # unpacked app under release/ (no installer)
```

These are ordinary packaging commands, not complete tagged payload builds.
Use [BUILDING.md](BUILDING.md) for the native bundled builder, Azure/Apple
signing, R2 artifact publication, and release gates. The current release matrix
publishes Windows and macOS packages; Linux AppImages build on canary tags as
unpublished diagnostic artifacts.

### How it works

The bundled app carries the Electron shell, native React chat surface, and
local agent payload. It runs the payload directly from resources. User data
lives in `HERMES_HOME` outside the app. Bootstrap builds instead provision a
source installation. A remote-only Light variant exists as a build target but
is not published.

The app has three boundaries:

- **Electron** resolves and validates a runnable backend, owns native
  filesystem/git/window capabilities, and exposes a narrow preload bridge.
- **React** owns the Desktop routes, panes, interaction state, and
  `@assistant-ui/react` transcript.
- **Hermes Agent** runs as a headless `hermes serve` process and exposes the
  `tui_gateway` JSON-RPC/WebSocket API. The renderer connects through
  [`apps/shared`](../shared/), which is also used by the browser dashboard.

A bundled artifact uses its payload. If that payload is unusable, the app
reports damage rather than installing a second checkout. It does not adopt
an arbitrary `hermes` command on PATH or a system Python installation.

Non-bundled builds can use the explicit source-root override, development
checkout, completed managed install, or `HERMES_DESKTOP_HERMES` deployment
override before offering bootstrap. Candidates are probed before use.
A runtime that predates `serve` falls back to headless
`dashboard --no-open`. This is compatibility for the backend command only and
does not launch or embed the dashboard UI.

The Electron orchestration entry point is `electron/main.ts`; pure resolution,
probe, hardening, and platform policies live in focused modules beside it. The
renderer is under `src/`, with shared atoms in `src/store` and transport/native
adapters in `src/lib`.

Before changing the app, read:

- [`AGENTS.md`](./AGENTS.md): architecture, state ownership, resolver/fallback,
  transport, performance, and testing rules.
- [`DESIGN.md`](./DESIGN.md): visual system, information architecture, motion,
  direct manipulation, and keyboard behavior.

### Connections, projects, and switching

Desktop supports a managed local backend, explicit remote gateways, and Hermes
Cloud connections. Remote and cloud modes use the same remote-capability path;
authentication and discovery differ, not the renderer feature model.

When no usable local runtime or saved remote connection exists, the first-run
screen offers **Connect to existing Hermes** before starting the local installer.
Desktop probes the gateway to discover token or OAuth authentication, requires a
successful HTTP and WebSocket connection test, and saves the connection using
the same encrypted Desktop configuration used by Settings. A saved remote
connection bypasses this choice on later launches. The regular Desktop build
still includes the local-install option; this is a remote operating mode, not a
separate client-only application.

In remote mode the gateway host is the execution boundary: agent tools,
terminal commands, and file operations run against the remote Hermes host, not
the computer displaying the Desktop UI.

Remote gateways that sit behind an access proxy may require extra headers on
every HTTP and WebSocket request. Configure them per connection in Settings →
Connections (Extra gateway headers), or add a `headers` object to Desktop's
Electron `userData/connection.json` remote block:

```json
{
  "mode": "remote",
  "remote": {
    "url": "https://hermes.example.com",
    "authMode": "token",
    "token": { "encoding": "safeStorage", "value": "..." },
    "headers": {
      "CF-Access-Client-Id": { "encoding": "safeStorage", "value": "..." },
      "CF-Access-Client-Secret": { "encoding": "safeStorage", "value": "..." }
    }
  }
}
```

Per-profile remote entries under `profiles[name].headers` use the same shape.
Desktop applies these headers only to matching remote gateway requests, treats
`https` and `wss` as the same gateway origin for WebSocket upgrades, and drops
transport- or Hermes-managed header names such as `Authorization`, `Cookie`,
`Host`, `Origin`, `Referer`, and `X-Hermes-Session-Token`.

Projects are the workspace abstraction. A project may own multiple folders,
repositories, worktrees, and sessions; a bare new chat remains detached unless
the user enters a project or configures a default project directory. Use the
Projects UI rather than adding a second per-session folder-picker workflow.

Changing profiles or connection modes is a soft workspace switch, not another
cold boot. The shell and current management overlay remain mounted while
gateway-bound nanostores are wiped, query-backed data is invalidated, and the
new connection repopulates skeletons. This prevents rows or transcripts from
the previous gateway bleeding into the next one. Switching changes only the
foreground view and request route: it does not cancel turns or stop a backend,
and retained background sockets continue receiving events from running jobs.

### Verification

Run before opening a PR (lint may surface pre-existing warnings but must exit cleanly):

```bash
pnpm run fix
pnpm run typecheck
pnpm run lint
pnpm run test:ui
pnpm run test:desktop:platforms
```

Run `pnpm run test:desktop:all` for install, boot, update, packaging, or other
release-path changes.

### Troubleshooting

Boot logs land in `HERMES_HOME/logs/desktop.log` (includes backend output and recent Python tracebacks) — check it first if the app reports a boot failure.

**macOS / Linux:**

```bash
# Force a clean first-launch setup
rm "$HOME/.hermes/hermes-agent/.hermes-bootstrap-complete"
# Rebuild a broken Python venv
rm -rf "$HOME/.hermes/hermes-agent/venv"
# Reset a stuck macOS microphone prompt (macOS only)
tccutil reset Microphone com.nousresearch.hermes
```

**Windows (PowerShell):**

```powershell
# Force a clean first-launch setup
Remove-Item "$env:LOCALAPPDATA\hermes\hermes-agent\.hermes-bootstrap-complete"
# Rebuild a broken Python venv
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\hermes\hermes-agent\venv"
```

> The default Hermes home on Windows is `%LOCALAPPDATA%\hermes`. Set the `HERMES_HOME` env var if you've relocated it.

---

## Community

- 💬 [Discord](https://discord.gg/NousResearch)
- 📖 [Documentation](https://hermes-agent.nousresearch.com/docs/)
- 🐛 [Issues](https://github.com/NousResearch/hermes-agent/issues)

---

## License

MIT — see [LICENSE](../../LICENSE).

Built by [Nous Research](https://nousresearch.com).
