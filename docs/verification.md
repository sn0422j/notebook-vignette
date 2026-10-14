# 検証記録

[開発ガイド](development.md)に記載した手順のうち、実施済みの範囲と未検証の項目を記録します。

## 設定の型付け・変換処理の分割 — 2026-10-12

- Linux / CPython 3.12.14
- pytest: 69件成功（従来の53件と、型付き設定・API互換性・再利用の16件）
- mypy 1.20.2: strictモードで13ファイルを検査し、エラーなし。公開APIの型の回帰検査を含む
- Ruff: コード検査・フォーマット検査に合格
- `uv lock --check`: 成功
- 日付と依存関係を固定し、default / dark / paperのサンプルHTMLがリファクタリング前とバイト単位で一致
- sdistからwheelをビルドし、ソース配布物の`docs/`・テストと、wheelのPythonモジュール・CSS・JavaScript・`py.typed`を確認
- ビルドしたwheelを`uv tool run --from …`で実行し、TOML・`--theme dark`・`--set`を併用したHTML変換に成功
- README・開発文書・変更履歴のローカルリンクとコードブロックを確認

HTMLの一致は同じサンプル・生成日付・依存関係で比較した結果です。すべてのNotebookや依存バージョンに対する完全一致を保証するものではありません。ブラウザ操作、OS、Pythonバージョンに関する未検証範囲は、下記の初回検証と同じです。

## 0.1.0 — 2026-10-12

- Linux / CPython 3.12.14
- nbconvert 7.17.1 / nbformat 5.11.1 / beautifulsoup4 4.15.0 / bleach 6.4.0
- pytest: 53件成功
- Ruff: 構文・インポート等の検査とフォーマット検査に合格
- sdistからwheelを生成し、CSS/JavaScriptを含むパッケージをビルド
- wheelを `uv tool run --from …` の隔離環境で起動し、サンプルNotebookのHTML変換を確認
- 3テーマのサンプルHTMLを生成

検証環境の`/proc`制約により`uvx`実行ファイルを直接起動できなかったため、同じ機能を提供する`uv tool run`でコマンド実行を確認しました。

ブラウザでの目視・クリック操作は未検証です。ブラウザ本体を用意できなかったため、HTML生成と構造の検証までを実施しています。数式用CDNの読み込み、OSごとのフォント表示、印刷レイアウトも未検証です。

Windows、macOS、およびPython 3.12以外での実行は、この記録の対象外です。GitHub ActionsにはPython 3.11〜3.14と3種類のOSの検証を設定していますが、上記の検証結果には含めていません。

ブラウザによる確認手順は、[開発ガイド](development.md)の「表示の確認」を参照してください。
