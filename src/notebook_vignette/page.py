"""ページの見出し・本文・注意事項・操作用アセットをひとつのHTMLへ組み立てる。"""

from __future__ import annotations

import html
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.resources import files

from pygments.formatters import HtmlFormatter

from .assets import PageAssets
from .content import NotebookBody
from .models import RenderConfig, ResolvedTheme
from .result import RenderReport
from .themes import theme_css

CSS = files("notebook_vignette").joinpath("assets/base.css").read_text(encoding="utf-8")
JS = files("notebook_vignette").joinpath("assets/controls.js").read_text(encoding="utf-8")


def display_date(date: str | None) -> str:
    """明示値、SOURCE_DATE_EPOCHのUTC日付、現在のローカル日付の順に採用する。"""
    if date is not None:
        return date
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    timestamp = (
        datetime.fromtimestamp(int(epoch), timezone.utc)
        if epoch is not None
        else datetime.now().astimezone()
    )
    return timestamp.strftime("%Y.%m.%d")


@dataclass(frozen=True, slots=True, kw_only=True)
class HtmlPage:
    """HTMLの組み立てに必要な値だけを保持する。Notebookの読み書きは行わない。"""

    body: NotebookBody
    assets: PageAssets
    report: RenderReport
    theme: ResolvedTheme
    config: RenderConfig
    language: str

    def render(self) -> str:
        """完全なHTML文書を返す。本文以外のユーザー由来テキストはエスケープする。"""
        date = display_date(self.config.date)
        title = html.escape(self.report.title)
        filename = html.escape(self.report.source.name)
        language = (" · " + html.escape(self.language)) if self.language else ""
        date_label = ("HTML生成 " + html.escape(date)) if date else ""
        layout_class = " no-toc" if not self.body.navigation else ""
        styles = self.assets.font_css + theme_css(self.theme) + CSS + self._syntax_css()
        return f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="generator" content="notebook-vignette">
<title>{title}</title><style>{styles}</style>{self.assets.math_html}</head>
<body><header class="masthead"><strong>NOTEBOOK / VIGNETTE</strong><span class="date">{date_label}</span></header>
<div class="layout{layout_class}">{self._sidebar()}<main>
<div class="toolbar"><span class="run-badge">{self.report.badge}</span>{self._code_button()}</div>
<h1 class="document-title">{title}</h1>
<div class="intro-meta">{filename}{language} · 保存済みの内容を表示</div>
{self.body.soup}
<footer><div class="footer-top"><span>NOTEBOOK VIGNETTE</span><a href="#">ページ先頭へ</a></div>
{self._notes()}{self.assets.font_license_html}</footer></main></div><script>{JS}</script></body></html>"""

    def _sidebar(self) -> str:
        if not self.body.navigation:
            return ""
        return (
            '<aside aria-label="目次"><div class="nav-title">CONTENTS</div><nav>'
            + self.body.navigation
            + '</nav><div class="nav-note">Notebookの保存済み内容<br>変換時の再実行なし</div></aside>'
        )

    def _code_button(self) -> str:
        if self.report.code_cells and not self.config.hide_code:
            return '<button id="toggle-code" type="button">コードを折りたたむ</button>'
        return ""

    def _notes(self) -> str:
        if not self.report.notes:
            return ""
        items = "".join("<li>" + html.escape(note) + "</li>" for note in self.report.notes)
        return '<ul class="format-notes">' + items + "</ul>"

    def _syntax_css(self) -> str:
        screen = HtmlFormatter(style=self.theme.syntax_style).get_style_defs(".highlight")
        print_style = HtmlFormatter(style="friendly").get_style_defs(".highlight")
        return str(screen) + "@media print{" + str(print_style) + "}"
