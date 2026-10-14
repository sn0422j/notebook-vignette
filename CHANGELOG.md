# Changelog

## 0.2.0

- READMEを利用者向けに整理し、開発ガイドと検証記録を`docs/`へ分離。
- ソース配布物に`docs/`を同梱。
- 設定を変更不可のdataclassへ移行し、CLI・Python API・テーマ解決で共通の型を使用。
- `AppConfig`、`RenderConfig`、`ThemeConfig`、`ColorOverrides`を公開APIへ追加。従来の引数形式も維持。
- `render_notebook`から本文変換・補助データ処理・ページ生成・保存を分離し、再利用できる`NotebookRenderer`とdocstringを追加。
- 戻り値に`RenderStats`の型定義を追加し、`py.typed`を同梱。mypyのstrict検査と型の回帰テストを追加。

## 0.1.0

- 保存済みNotebookのHTML変換、目次生成、コードの折りたたみとコピー操作。
- `uvx --from`、Python API、`python -m` に対応したsrc構成。
- default / dark / paper、TOML・Notebook metadata・CLIによるテーマ設定。
- 複数入力、フォルダ走査、JSON結果、上書き保護、原子的な出力。
- HTML全体のサニタイズと、ローカル画像の参照範囲制限。
- 設定エラー、出力の欠落・代替表示、外部依存を明示。

単体スクリプトからの移行については、[開発ガイド](docs/development.md)を参照してください。
