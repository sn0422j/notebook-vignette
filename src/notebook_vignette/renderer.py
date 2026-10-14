"""型付き設定を用いてNotebook変換の各段階を調整する公開エントリーポイント。"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import nbformat
from nbformat import NotebookNode

from .assets import prepare_assets
from .config import parse_theme_config
from .content import NotebookConverter
from .models import (
    AppConfig,
    ConfigOverrides,
    MathJaxMode,
    RenderOverrides,
    ResolvedTheme,
    ThemeConfig,
)
from .output import RenderPaths, write_html
from .page import HtmlPage
from .result import RenderReport, RenderStats
from .themes import resolve_theme


class NotebookRenderer:
    """設定を保持し、読み込み・本文変換・ページ生成・保存を調整する。

    1回の変換に固有の本文や注意事項はインスタンスに保持しないため、同じ
    インスタンスを複数Notebookへ再利用できる。Notebookは実行・変更しない。
    """

    def __init__(self, config: AppConfig | None = None) -> None:
        self._config = config or AppConfig()

    def render(
        self, notebook: str | Path, output: str | Path | None = None, *, overwrite: bool = False
    ) -> RenderStats:
        """Notebookを読み込み、完成したHTMLを保存して集計結果を返す。

        変換失敗時は例外を呼び出し元へ伝え、既存HTMLを変更しない。
        overwrite=Falseで既存出力がある場合はFileExistsErrorを送出する。
        """
        paths = RenderPaths.resolve(notebook, output, self._config.render, overwrite=overwrite)
        notebook_node = nbformat.read(paths.source, as_version=4)  # type: ignore[no-untyped-call]
        theme = self._theme_for(notebook_node)
        notes: list[str] = []
        body = NotebookConverter(self._config.render).convert(notebook_node, paths.source, notes)
        assets = prepare_assets(
            body.soup, paths.source, paths.destination, self._config.render, notes
        )
        report = RenderReport.collect(
            notebook_node,
            body,
            paths.source,
            paths.destination,
            assets.embedded_local_images,
            notes,
            theme.name,
        )
        page = HtmlPage(
            body=body,
            assets=assets,
            report=report,
            theme=theme,
            config=self._config.render,
            language=str(notebook_node.metadata.get("language_info", {}).get("name", "")),
        )
        write_html(page.render(), paths.destination, overwrite=overwrite)
        return report.to_dict()

    def _theme_for(self, notebook: NotebookNode) -> ResolvedTheme:
        """Notebookのテーマよりアプリ設定を優先し、確定テーマへ変換する。"""
        metadata = notebook.metadata.get("vignette", {})
        if not isinstance(metadata, Mapping):
            raise ValueError("metadata.vignette はオブジェクトで指定してください。")
        inline = parse_theme_config(metadata.get("theme", {}))
        # Validate styles in both sources, even when a higher-priority value masks one.
        resolve_theme(inline)
        return resolve_theme(inline.overlay(self._config.theme))


def render_notebook(
    notebook: str | Path,
    output: str | Path | None = None,
    *,
    config: AppConfig | None = None,
    title: str | None = None,
    collapse_code: bool | None = None,
    hide_code: bool | None = None,
    toc_depth: int | None = None,
    mathjax: MathJaxMode | None = None,
    mathjax_js: str | Path | None = None,
    font: str | Path | None = None,
    font_license: str | Path | None = None,
    trusted_html: bool | None = None,
    theme: ThemeConfig | Mapping[str, object] | None = None,
    allow_outside_assets: bool | None = None,
    date: str | None = None,
    overwrite: bool = False,
) -> RenderStats:
    """保存済みNotebookをHTMLへ変換する。実際の処理はNotebookRendererへ委譲する。

    Args:
        notebook: 入力.ipynbのパス。カーネルは起動しない。
        output: 出力HTML。省略時はNotebookと同名の.html。
        config: 再利用できるAppConfig。省略時は既定設定。
        theme: configのテーマを上書きするThemeConfig。互換性のため辞書も受け付ける。
        overwrite: 既存HTMLの上書きを許可するか。
        その他のキーワード引数: 指定された値だけでconfig.renderを上書きする。
            Noneは指定なし。Falseと空文字は明示的な上書きとして扱う。
            補助ファイルの文字列パスは、この境界でPathへ変換する。

    Returns:
        件数、出力パス、注意事項を含むJSON互換のRenderStats辞書。

    Raises:
        ValueError: 設定、入力形式、出力先が不正な場合。
        FileExistsError: 出力済みでoverwrite=Falseの場合。
        OSError: 入力や補助ファイルの読み込み、出力の保存に失敗した場合。
    """
    overrides = RenderOverrides(
        title=title,
        collapse_code=collapse_code,
        hide_code=hide_code,
        toc_depth=toc_depth,
        mathjax=mathjax,
        mathjax_js=Path(mathjax_js) if mathjax_js else None,
        font=Path(font) if font else None,
        font_license=Path(font_license) if font_license else None,
        trusted_html=trusted_html,
        allow_outside_assets=allow_outside_assets,
        date=date,
    )
    theme_config = (
        theme
        if isinstance(theme, ThemeConfig)
        else parse_theme_config(theme if theme is not None else {})
    )
    settings = (config or AppConfig()).apply(ConfigOverrides(render=overrides, theme=theme_config))
    return NotebookRenderer(settings).render(notebook, output, overwrite=overwrite)
