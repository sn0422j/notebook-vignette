# 開発ガイド

notebook-vignetteの変更、検証、配布を行う開発者向けの手順です。コマンドの使い方とテーマ設定は[README](../README.md)、実施済みの検証範囲は[検証記録](verification.md)を参照してください。

## 開発環境

Python 3.11以上とuvを使用します。以下のコマンドはリポジトリのルートで実行してください。

```bash
uv sync --locked
```

`uv.lock`に従って開発用の仮想環境を作成し、実行時の依存関係とpytest・Ruff・mypy・buildを用意します。

## コード構成

| パス | 役割 |
| --- | --- |
| `src/notebook_vignette/cli.py` | 引数の解析、入力探索、出力先の事前確認、バッチ実行 |
| `src/notebook_vignette/models.py` | 設定・色・確定テーマのdataclass、値の検証と合成 |
| `src/notebook_vignette/config.py` | TOML・CLI・metadataなどの外部入力を型付き設定へ変換 |
| `src/notebook_vignette/themes.py` | プリセットの解決、`ResolvedTheme`からCSS変数の生成 |
| `src/notebook_vignette/renderer.py` | 公開関数と、各変換段階を調整する`NotebookRenderer` |
| `src/notebook_vignette/content.py` | nbconvertの設定、本文変換、サニタイズ、目次・コード操作 |
| `src/notebook_vignette/assets.py` | 画像・リンク・MathJax・フォントの処理 |
| `src/notebook_vignette/page.py` | 本文・補助データ・テーマからHTMLページを組み立て |
| `src/notebook_vignette/result.py` | 集計用`RenderReport`と公開結果の`RenderStats` |
| `src/notebook_vignette/output.py` | 入出力パスの検証と、完成したHTMLの保存 |
| `src/notebook_vignette/assets/` | 基本CSSとコード操作用JavaScript |
| `src/notebook_vignette/__init__.py` | 公開Python APIとバージョン |
| `tests/` | 変換、設定、コマンド処理の回帰テスト |
| `examples/` | サンプルNotebook、設定、生成HTML |
| `pyproject.toml` | パッケージ情報、依存関係、ビルド・検査設定 |
| `uv.lock` | 開発・継続的インテグレーション用の依存関係ロック |
| `.github/workflows/ci.yml` | GitHub Actionsの検証手順 |

コマンドのエントリーポイントは`notebook-vignette`と`render-vignette`です。どちらも`notebook_vignette.cli:main`を呼び出します。

### 設定の型と優先順位

設定の共通型を`models.py`に置き、CLI、Python API、テーマ解決、レンダラーから参照します。辞書は外部入力の解析とJSON互換の結果・CSS変数への変換に限定します。内部で`dict[str, Any]`を設定として受け渡しません。

| 型 | 用途 |
| --- | --- |
| `AppConfig` | 変換設定とテーマ設定をまとめる公開APIの設定 |
| `RenderConfig` | 既定値を補い、項目間の整合性も検証した変換設定 |
| `RenderOverrides` / `ConfigOverrides` | CLIなどで明示された項目だけを持つ部分設定 |
| `ThemeConfig` / `ColorOverrides` | テーマと色の部分設定。未指定の項目は継承 |
| `ResolvedTheme` / `ColorPalette` | プリセットまで解決し、全項目の値が決まった描画用テーマ |

これらは`frozen=True, slots=True, kw_only=True`のdataclassです。テーマ名とMathJaxモードは`Literal`、色は個別の属性、補助ファイルは`Path`で表現します。変更は`apply`・`overlay`で新しいオブジェクトを作り、元の設定を保持します。部分設定の`None`は継承を意味し、真偽値の`False`や日付の空文字を未指定と混同しません。

CLIはTOML、通常のオプション、`--set`の順に設定を重ねます。Notebookのテーマは各変換で読み取り、アプリ設定より低い優先順位で合成します。色は項目単位で継承するため、テーマ名の変更だけで明示済みの色は消えません。

`config.py`が未知のキーや外部の値の型を検証し、dataclassが値の制約と組み合わせを検証します。Pygmentsのスタイル名の存在確認は`themes.resolve_theme`が担当します。

### 変換の責務

`render_notebook`は公開APIの引数を型付き設定へまとめ、`NotebookRenderer`へ委譲します。従来のキーワード引数とテーマ辞書は、この入口で互換性を保ちます。

`NotebookRenderer.render`は、パス検証、Notebook読み込み、テーマ解決、本文変換、補助データ処理、集計、ページ生成、保存を順に呼び出します。HTMLを加工する詳細やファイル保存の詳細をこのメソッドへ追加しないでください。

`NotebookConverter`はnbconvertの設定と本文変換をカプセル化し、`HtmlPage`はページ生成を担当します。各段階の結果は`NotebookBody`、`PageAssets`、`RenderReport`で受け渡します。変換ごとの注意事項と解析木はローカル変数に保持し、同じ`NotebookRenderer`を使っても前のNotebookの状態を引き継ぎません。

## 実装上の方針

- Notebookは読み取り専用として扱い、変換にはコピーを使用します。カーネルを起動せず、保存済み出力を表示します。
- Markdownと標準出力形式の変換にはnbconvertを使用し、目次やコード操作などを追加します。
- 設定ファイルはTOMLとして読み込み、Pythonコードを実行する設定方式は使用しません。
- Notebookのmetadataから受け付けるのはテーマ情報だけです。ファイルパスや信頼設定を読み込ませません。
- テーマの値は許可されたキー・型・値の形式を検証してからCSSへ変換します。
- 既定ではHTMLをサニタイズし、ローカル画像の取り込み範囲をNotebookのフォルダ内に制限します。
- 表示できない形式は保存データや注意事項として残します。
- HTMLを完成させてから出力ファイルを確定し、変換途中の失敗で既存HTMLを破損させないようにします。

### 出力ファイルの確定

出力先と同じフォルダに一時ファイルを作成します。上書き時は`os.replace`、上書き禁止時は`os.link`で出力を確定します。後者は同一ファイルシステム上のハードリンク機能を必要とします。

この保護はファイル単位です。バッチ全体を一括で取り消す機能はありません。設定エラーや出力名の衝突は処理開始前に確認し、変換中のファイル単位の失敗は記録して残りの入力を処理します。

### 外部ライブラリとの境界

nbconvertの`basic`テンプレートが生成するHTML構造を利用しています。コードセルと出力HTMLの対応、添付画像処理、サニタイズの適用箇所は、nbconvert更新時の重点確認箇所です。

`markdown_filter`ではnbconvertのMarkdownレンダラーを拡張しています。非公開メソッド`_embed_image_or_attachment`に依存するため、nbconvertの互換範囲を変更する際は添付画像の回帰テストを確認してください。

mypyは自前の全モジュールをstrictモードで検査します。型情報のない外部ライブラリのimportは許容し、nbformatの読み込みとnbconvertのコンストラクタには対象のエラーコードを限定した`type: ignore`を付けています。外部ライブラリの型情報が更新されたら、これらの例外を見直してください。

## テストと静的検査

```bash
uv run --no-sync pytest
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync mypy
```

整形を適用する場合は`uv run --no-sync ruff format .`を実行します。

テストは、空Notebook・未実行セル・エラー出力、標準と独自の出力形式、添付画像、画像パスの境界、テーマの優先順位、設定エラー、出力保護、バッチ処理を対象にしています。

`tests/test_typed_config.py`では設定の不変性、部分設定の合成、型付きAPIと従来APIの出力一致、レンダラーの再利用を確認します。`tests/typecheck/public_api.py`はmypy専用で、公開APIの型推論と不正な設定の静的検出を確認します。後者はpytestでは実行しません。

`examples/showcase.ipynb`は保存済み表示の検証用で、未実行セルやエラーの例を含みます。Notebook全体の実行は検証手順に含めず、Ruffの対象からも除外しています。

GitHub ActionsではLinux・Windows・macOSとPython 3.11〜3.14の組み合わせに対して、依存関係の同期、Ruff、mypy、pytest、ビルド、コマンドによるサンプル変換を実行します。実際の実行結果は各ワークフローの記録で確認してください。

## 表示の確認

```bash
uv run --no-sync notebook-vignette examples/showcase.ipynb -o preview-default.html --theme default --mathjax none --force
uv run --no-sync notebook-vignette examples/showcase.ipynb -o preview-dark.html --theme dark --mathjax none --force
uv run --no-sync notebook-vignette examples/showcase.ipynb -o preview-paper.html --theme paper --mathjax none --force
```

生成HTMLをブラウザで開き、以下を確認します。

1. 日本語、表、画像、エラー出力が読めること。
2. 目次のリンク、コードの開閉、コピー操作が動作すること。
3. 狭い画面でページ全体に不要な横スクロールが生じないこと。
4. 印刷時にコードが展開され、テーマに関わらず文字が読めること。
5. 数式を含むNotebookで`--mathjax auto`とローカル埋め込みの表示を確認すること。

上記のプレビュー生成コマンドは`--mathjax none`を使用するため、数式はTeXのまま表示されます。数式描画の確認は別途行います。

## 依存関係の更新と再現性

```bash
uv lock --upgrade
uv sync --locked
uv run --no-sync pytest
```

`pyproject.toml`は利用可能な依存バージョンの範囲を宣言し、`uv.lock`は開発・検証に用いる具体的な解決結果を記録します。更新後は静的検査、ビルド、表示の確認も実施してください。

**`uvx --from git+…`は、リポジトリ内の`uv.lock`で依存関係を固定しません。** パッケージのメタデータに従って解決します。タグやコミットの指定はソースを固定しますが、依存関係まで同一にするものではありません。

依存関係を含めた検証環境の再現には、対象リビジョンのリポジトリを取得し、`uv sync --locked`と`uv run --no-sync`を使います。

HTMLの生成日付は`--date`で固定・非表示にできます。`SOURCE_DATE_EPOCH`を設定した場合は、UTCの日付を使用します。ただし外部ライブラリや入力に由来する差異まで含めた、バイト単位の完全一致は保証しません。

## ビルドと配布物の確認

```bash
uv build
```

`dist/`にソース配布物とwheelを生成します。ソース配布物には`docs/`を含め、wheelには実行に必要なPythonモジュール、CSS、JavaScript、型情報の提供を示す`py.typed`とパッケージ情報を含めます。

ビルドしたwheelを使って、パッケージにリソースが同梱されていることを確認します。ファイル名のバージョンはビルド結果に合わせてください。

```bash
uvx --from ./dist/notebook_vignette-0.1.0-py3-none-any.whl notebook-vignette examples/showcase.ipynb -o wheel-smoke.html --mathjax none --force
```

## リリース

1. `pyproject.toml`と`src/notebook_vignette/__init__.py`のバージョンを揃えます。
2. `CHANGELOG.md`に変更内容と互換性に影響する変更を記載します。
3. 必要に応じて`uv.lock`を更新し、検査・ビルド・表示確認を完了します。
4. 配布文書のリポジトリURLとバージョン表記を確認します。初回公開時はREADMEの`OWNER`を実際の所有者へ置き換えます。
5. GitHub Actionsの成功を確認し、バージョンに対応する`v0.1.0`などのタグを作成します。
6. リリースノートと配布物を公開し、タグを指定したコマンドで変換を確認します。

再現性が必要な運用では、利用するソースを完全なコミットハッシュで固定する方法がおすすめです。依存関係の固定方法は前節を参照してください。

## 単体スクリプトからの移行

前身の`render_vignette.py`から移行する場合、次の挙動の違いに注意してください。

| 項目 | パッケージ版の挙動 |
| --- | --- |
| Python | 3.11以上が必要 |
| 入力引数 | コマンドでは明示的な入力指定が必要 |
| フォルダ引数 | コマンドではフォルダ内のNotebookを対象にする |
| 既存HTML | `--force`、Python APIでは`overwrite=True`で上書き |
| フォルダ外の画像 | `--allow-outside-assets`で取り込みを許可 |
| 標準出力 | 既定はテキスト。`--json`は結果の配列を返す |

## 参考資料

- [uvのツール実行とGitソース](https://docs.astral.sh/uv/guides/tools/)
- [uvの隔離環境とキャッシュ](https://docs.astral.sh/uv/concepts/tools/)
- [nbconvertのエクスポーター](https://nbconvert.readthedocs.io/en/latest/api/exporters.html)
- [nbconvertのテンプレート](https://nbconvert.readthedocs.io/en/latest/customizing.html)
- [nbconvertのリリース](https://github.com/jupyter/nbconvert/releases)
