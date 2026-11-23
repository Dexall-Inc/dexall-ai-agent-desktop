# hermes_platform/ — マシン情報とリソース検索

ルートの `AGENTS.md` の上に適用される。

**マシン情報とリソース検索は `hermes_platform` を通して行う。** `hermes_platform.host` は、
OS ファミリー、ネイティブアーキテクチャ（`IsWow64Process2` → `platform.machine()`。x64-on-ARM64
エミュレーション下では `PROCESSOR_ARCHITECTURE` 単体では AMD64 と読まれるため、それだけに
依存しない）、CPU 識別、WSL/コンテナ/Termux の唯一の答えである。情報はプロセスごとにキャッシュされ、
**環境変数の入力を受け取らない**。そのため、ハードウェア認識器（`host/products.py`）をシェルから
設定することはできない。制御ホスト（この Python が実行される場所）と、ターミナル実行ターゲット
（SSH/コンテナ）、そして Desktop クライアント（別のマシン）を区別すること。`host.*` が答えるのは
最初のものだけである。`hermes_platform/` の外に新規の素の `shutil.which` や手書きの既知パス表を
置くと、理由を付けて許可リストに登録しない限り `tests/test_managed_runtime_resolution.py` に
失敗する。リゾルバは `hermes_platform/resolver/` に置くこと。検索は何もインストール・ダウンロード・
起動しない。