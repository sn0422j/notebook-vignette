# notebook-vignette

Jupyter Notebookを、目次・コードの折りたたみ・コピー操作付きのHTMLレポートに変換します。表、画像、数式、標準出力、エラー出力を表示し、テーマ設定と複数ファイルの一括変換に対応しています。

## クイックスタート

Python 3.11以上と[uv](https://docs.astral.sh/uv/)が必要です。

```bash
uvx --from "git+https://github.com/sn0422j/notebook-vignette.git" notebook-vignette analysis.ipynb
```

同じフォルダに `analysis.html` ができます。すでにある場合は `--force` が必要です。

リポジトリを取得済みの場合は、そのルートディレクトリから実行できます。

```bash
uvx --from . notebook-vignette examples/showcase.ipynb -o report.html
uvx --from . notebook-vignette examples/showcase.ipynb -o dark.html --theme dark
```

`uvx`は`uv tool run`の別名です。既存プロジェクトやグローバルPythonへのパッケージ追加は行わず、隔離した環境で動作します。ただし依存パッケージの取得・内部インストールとキャッシュは発生します。

依存パッケージのキャッシュを残したくないとき:

```bash
uvx --no-cache --from "git+https://github.com/sn0422j/notebook-vignette.git" notebook-vignette analysis.ipynb
```

**Notebookは実行しません。** Python / R / Juliaなど、カーネルに関わらず保存されたMarkdown・コード・出力を表示します。Notebookのライブラリやカーネルをレンダリング環境へ入れる必要はありません。

Notebookの実行もCLIから行いたいとき:

```bash
uv run --with nbconvert --with ipykernel python -m nbconvert \
  analysis.ipynb \
  --to notebook --execute \
  --output analysis.executed \
  --ExecutePreprocessor.timeout=600
```

## コマンド例

以下の例では実行コマンドを`notebook-vignette`と表記します。`uvx`を使う場合は、`uvx --from . notebook-vignette`、または前節のGitHubからの実行形式に置き換えてください。

```bash
# 出力先、タイトル、コード折りたたみ
notebook-vignette analysis.ipynb -o report.html --title "分析結果" --collapse-code

# 入力コードをHTMLに含めない（出力は残る）
notebook-vignette analysis.ipynb --hide-code --force

# 複数ファイル / フォルダ / glob（引用符付きも対応）
notebook-vignette a.ipynb b.ipynb --output-dir reports
notebook-vignette notebooks --recursive --output-dir reports
notebook-vignette "notebooks/*.ipynb" --output-dir reports

# 設定ファイルと、その場での上書き
notebook-vignette analysis.ipynb --config examples/vignette.toml
notebook-vignette analysis.ipynb --theme dark --set 'theme.colors.accent=#81d8cc'
notebook-vignette analysis.ipynb --set 'theme.font_size=17px' --set 'render.toc_depth=2'

# パイプライン用（標準出力は結果のJSON配列、診断は標準エラー）
notebook-vignette notebooks -r --output-dir reports --json

# テーマ・全色名の一覧
notebook-vignette --list-themes
```

`render-vignette`も同じコマンドの別名です。全オプションは`--help`で確認できます。

フォルダ指定時はフォルダ内の相対階層を出力先へ再現します。個別ファイル/glob指定時はファイル名を使用し、複数の入力が同じ出力先になる場合は処理開始前にエラーにします。`.ipynb_checkpoints` はフォルダ探索から除外します。

あるファイルの変換が失敗しても、残りのファイルを処理します。診断メッセージは標準エラー出力へ、通常の結果または`--json`の結果は標準出力へ出力します。

| 終了コード | 意味 |
| --- | --- |
| `0` | 全件成功 |
| `1` | 変換失敗あり |
| `2` | 引数・設定・入力計画のエラー |

## テーマ設定

| テーマ | 配色 |
| --- | --- |
| `default` | 青緑をアクセントにした白い紙面 |
| `dark` | 暗い背景と明るい文字 |
| `paper` | 暖色の背景と紙面 |

設定ファイルは`--config`で読み込みます。以下を`vignette.toml`などの名前で保存し、`--config vignette.toml`を指定してください。[設定例](examples/vignette.toml)も参照できます。

```toml
[render]
collapse_code = true
toc_depth = 3
mathjax = "auto"

[theme]
name = "default"
syntax_style = "friendly"  # Pygmentsのスタイル名
content_width = "1240px"
font_size = "15px"
line_height = 1.94
font_family = "VignetteJP, 'Noto Sans JP', 'Yu Gothic', Meiryo, sans-serif"
mono_font_family = "'DejaVu Sans Mono', Consolas, monospace"

[theme.colors]
accent = "#087f8c"
ink = "#18334c"
text = "#293c4d"
muted = "#586879"
paper = "#ffffff"
background = "#f1f4f6"
line = "#dfe6eb"
```

`theme.colors`には、表・コード・警告などの細かな色も指定できます。全キーは `--list-themes` で取得してください。色は16進表記（3/4/6/8桁）、寸法は正の`px`・`rem`・`em`のみ許可します。未知のキーや型を拒否し、誤記を黙って無視しません。テーマの値として任意のCSSやJavaScriptは受け付けません。

Notebook内に持たせる場合は、Notebook全体のmetadataへ次の値を入れます。Markdown本文やコードセル内ではありません。

```json
{
  "vignette": {
    "theme": {
      "name": "paper",
      "colors": {"accent": "#916333"}
    }
  }
}
```

優先順位は **組み込み値 < Notebookのテーマ情報 < TOML < 通常のCLIオプション < `--set`** です。テーマのテーブルはキー単位でマージします。`--theme dark`だけを指定しても、低優先度で明示された個別の色は残ります。Notebook metadataから信頼設定・補助ファイルのパス・出力先は読みません。

設定ファイルは`--config`で明示的に読み込みます。自動探索はしません。TOML内のフォント・MathJax等の相対パスはその設定ファイル基準、CLIのパスは作業ディレクトリ基準です。

`[render]` の全キーは `title`, `collapse_code`, `hide_code`, `toc_depth`, `mathjax`, `mathjax_js`, `font`, `font_license`, `trusted_html`, `allow_outside_assets`, `date`。コマンドの`--show-code`は設定で閉じたり隠したりしたコードを再表示します。真偽値は`--set render.hide_code=false`等でも上書きできます。

## 対応範囲と限界

Notebookの保存済み内容を静的なHTMLとして表示します。任意の対話機能や外部サービスの完全再現は対象外です。

| 内容 | 挙動 |
|---|---|
| Markdown、見出し、表、コード、標準出力、エラー | 表示。空Notebook・未実行セルも対応 |
| Python以外のカーネル | カーネル不要。保存内容と利用可能な構文強調で表示 |
| PNG / JPEG / SVG | 保存出力を埋め込み。SVGは画像として表示 |
| GIF / WebP / AVIF / BMP | 保存画像を埋め込み（ブラウザ対応に依存） |
| Markdown添付画像・ローカル画像 | 埋め込み。ローカル相対パスはNotebook基準 |
| HTML表・数式出力 | HTMLの危険な要素を除去。数式はMathJax設定に従う |
| rawセル | HTML指定ならHTML、それ以外は元テキストを表示 |
| Widget / Plotly / Vegaなどの独自MIME | 保存された標準の静的形式があれば表示。なければ形式名とデータを表示 |
| Mermaid・独自拡張・JavaScript依存出力 | 完全な再現対象外。静的内容/代替データを優先 |
| 壊れたJSON、不正なNotebookスキーマ | 明示的に失敗。内容を推測して修復しない |
| PDFとしての出力 | 未対応。生成HTMLをブラウザで印刷可能 |

Notebookは書き換えません。未実行の計算を補ったり、Python変数から出力を復元したりはしません。入力コード非表示は秘密情報の除去機能ではなく、保存済み出力には値やエラーが残ります。

標準で入力HTMLをサニタイズし、script・イベント属性・iframe等を取り除きます。表の一部のCSSなど、元の見た目が変わる場合があります。`--trusted-html`は入力HTML/JavaScriptを保持しますが、Widget状態の復元やJavaScriptライブラリの自動注入は行いません。ブラウザで入力スクリプトが動作し得るため、自分で信頼できるNotebookだけに使ってください。これはPythonコード実行の許可とは別です。

ローカル画像は、既定でNotebookのフォルダとその配下だけを取り込みます。`../`・絶対パス・シンボリックリンクで範囲外に出る画像は取り込みません。必要なら `--allow-outside-assets` を明示します。外部画像・CSS・JavaScriptを変換時にダウンロードしません。ただし生成HTMLを開くと、残っている外部画像等への通信が発生し得ます。

## 数式・フォント・オフライン

```bash
# 数式を検出した場合だけ固定版のMathJax 3をCDNから読み込む（既定）
notebook-vignette analysis.ipynb --mathjax auto

# TeXをそのまま表示し、MathJaxを読み込まない
notebook-vignette analysis.ipynb --mathjax none

# 手元のMathJaxバンドルと、任意の日本語フォントを埋め込む
notebook-vignette analysis.ipynb --mathjax-js assets/tex-svg-full.js \
  --font assets/ipaexg.ttf --font-license assets/IPA_Font_License.txt
```

生成HTMLには基本のCSS、コード操作用JavaScript、保存された画像を埋め込みます。外部画像・リンク先ファイル・対話出力の依存ライブラリは自動収集しません。MathJaxの追加拡張にも通信が必要な場合があるため、単一HTMLであることと完全オフライン対応は別です。変換結果の`notes`とHTML末尾に制約を表示します。

## Python API

Python APIを使う場合は、利用側のプロジェクトにこのパッケージを依存関係として追加してください。`uvx`の隔離環境にあるパッケージは、利用側のPython環境から直接インポートできません。

```python
from notebook_vignette import (
    AppConfig,
    ColorOverrides,
    RenderConfig,
    ThemeConfig,
    render_notebook,
)

config = AppConfig(
    render=RenderConfig(collapse_code=True, mathjax="none"),
    theme=ThemeConfig(name="dark", colors=ColorOverrides(accent="#81d8cc")),
)

stats = render_notebook(
    "analysis.ipynb",
    "report.html",
    config=config,
    overwrite=True,
)
print(stats["notes"])
```

設定は変更不可のdataclassで、テーマ名・色名・値の型をエディタや型チェッカーで確認できます。補助ファイルは`RenderConfig(font=Path("font.woff2"))`のように`pathlib.Path`で指定します。値の形式や設定の組み合わせは実行時にも検証します。

同じ設定で繰り返し変換する場合は、`NotebookRenderer(config).render(...)`を使えます。TOMLから設定を作る場合は、`notebook_vignette.config.load_config(Path("vignette.toml"))`で`AppConfig`を取得できます。

APIで指定したテーマはNotebookのテーマ情報より優先します。`render_notebook(..., config=config, hide_code=False)`のような個別引数は、設定オブジェクトの値を上書きします。`None`は指定なしとして扱い、`False`と空文字は上書きに使えます。従来の個別引数と`theme={...}`形式も引き続き利用できます。戻り値は、キーと値の型を定義した`RenderStats`（`TypedDict`）です。

## 生成日付の指定

表示する日付は`--date 2026.10.12`のように指定できます。非表示にする場合は`--date ''`を指定します。省略時は変換時の日付を表示します。

## 開発・ライセンス

開発環境、テスト、ビルド、リリースの手順は[開発ガイド](docs/development.md)を参照してください。変更履歴は[CHANGELOG](CHANGELOG.md)に記載しています。

[MIT License](LICENSE)
