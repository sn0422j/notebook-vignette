"""Notebook本文の変換、サニタイズ、目次とコード操作の付与。"""

from __future__ import annotations

import base64
import copy
import html
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, unquote

import bleach
from bleach.css_sanitizer import CSSSanitizer
from bs4 import BeautifulSoup
from jinja2 import pass_context
from jinja2.runtime import Context
from nbconvert import HTMLExporter
from nbconvert.filters.highlight import Highlight2HTML
from nbconvert.filters.markdown_mistune import IPythonRenderer, MarkdownWithMath
from nbformat import NotebookNode
from traitlets.config import Config

from .models import RenderConfig


@dataclass(frozen=True, slots=True)
class NotebookBody:
    """変換済みの本文とナビゲーション。HTMLの解析木はこの変換内でのみ変更する。"""

    soup: BeautifulSoup
    title: str
    navigation: str


class NotebookConverter:
    """nbconvertとHTML加工の詳細を隠蔽し、保存済みNotebookから本文を生成する。"""

    def __init__(self, config: RenderConfig) -> None:
        self._config = config

    def convert(self, notebook: NotebookNode, source: Path, notes: list[str]) -> NotebookBody:
        """入力をコピーして変換し、タイトル・目次・コード操作付きの本文を返す。

        notebookは変更しない。表示の代替処理に関する注意事項をnotesへ追記する。
        """
        working = copy.deepcopy(notebook)
        prepare_outputs(working, notes, self._config.trusted_html)
        exporter = self._exporter(working, notes)
        fragment, _ = exporter.from_notebook_node(
            working, resources={"metadata": {"path": str(source.parent), "name": source.stem}}
        )
        soup = BeautifulSoup(
            fragment if self._config.trusted_html else clean_html(fragment), "html.parser"
        )
        for anchor in soup.select("a.anchor-link"):
            anchor.decompose()
        first_h1 = soup.select_one(".text_cell_render h1")
        title = str(
            self._config.title
            or notebook.metadata.get("title")
            or (first_h1.get_text(" ", strip=True) if first_h1 else source.stem)
        )
        navigation = make_toc(soup, title, self._config.toc_depth)
        add_code_controls(soup, notebook, self._config.collapse_code, self._config.hide_code)
        return NotebookBody(soup, title, navigation)

    def _exporter(self, notebook: NotebookNode, notes: list[str]) -> HTMLExporter:
        """コード実行を無効にし、この変換専用のフィルタを持つExporterを作成する。"""
        config = Config()
        config.NbConvertBase.display_data_priority = STATIC_MIMES
        config.TagRemovePreprocessor.enabled = False
        config.ExecutePreprocessor.enabled = False
        exporter = HTMLExporter(  # type: ignore[no-untyped-call]  # nbconvert's constructor lacks annotations.
            template_name="basic",
            config=config,
            sanitize_html=not self._config.trusted_html,
            embed_images=False,
        )
        language = notebook.metadata.get("language_info", {})
        lexer = language.get("pygments_lexer", language.get("name", "text"))
        if lexer in {"ipython", "ipython2", "ipython3"}:
            lexer = "python3"
        exporter.filters = {
            "clean_html": clean_html,
            "markdown2html": markdown_filter(notes),
            "highlight_code": Highlight2HTML(pygments_lexer=lexer),  # type: ignore[no-untyped-call]
        }
        return exporter


STATIC_MIMES = [
    "text/html",
    "text/markdown",
    "image/svg+xml",
    "image/png",
    "image/jpeg",
    "text/latex",
    "text/plain",
]
WIDGET_MIME = "application/vnd.jupyter.widget-view+json"


def markdown_filter(notes: list[str]) -> Callable[[Context, str], str]:
    """Keep a missing/unsupported attachment from aborting the whole notebook."""

    class AttachmentRenderer(IPythonRenderer):
        def _embed_image_or_attachment(self, src: str) -> str:
            if not src.startswith("attachment:"):
                return src  # Local image reads go through our path-boundary check.
            name = unquote(src[len("attachment:") :])
            data = self.attachments.get(name, {})
            for mime in (
                "image/svg+xml",
                "image/png",
                "image/jpeg",
                "image/gif",
                "image/webp",
                "image/avif",
                "image/bmp",
            ):
                if mime in data:
                    payload = text(data[mime])
                    if mime == "image/svg+xml" and "<" in payload:
                        payload = base64.b64encode(payload.encode("utf-8")).decode("ascii")
                    return f"data:{mime};base64,{payload}"
            notes.append(f"添付画像が未保存または非対応です: {name}")
            return src

    @pass_context
    def render(context: Context, source: str) -> str:
        renderer = AttachmentRenderer(
            escape=False,
            embed_images=False,
            attachments=context.get("cell", {}).get("attachments", {}),
        )
        return str(MarkdownWithMath(renderer=renderer).render(source))

    return render


def clean_html(fragment: object) -> str:
    """見出し・表・画像を残すHTMLフィルタ。生成する操作用JSには適用しない。"""
    parsed = BeautifulSoup(str(fragment), "html.parser")
    for tag in parsed.select(
        "script, style, iframe, object, embed, link, meta, base, form, input, button"
    ):
        tag.decompose()
    # Standalone SVG in an image context does not execute scripts in the page.
    for svg in parsed.find_all("svg"):
        image = parsed.new_tag("img", alt="SVG出力")
        image["src"] = "data:image/svg+xml;base64," + base64.b64encode(str(svg).encode()).decode()
        svg.replace_with(image)
    tags = set(bleach.sanitizer.ALLOWED_TAGS) | {
        "p",
        "div",
        "pre",
        "code",
        "span",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "table",
        "thead",
        "tbody",
        "tfoot",
        "tr",
        "td",
        "th",
        "caption",
        "colgroup",
        "col",
        "img",
        "figure",
        "figcaption",
        "br",
        "hr",
        "sub",
        "sup",
        "s",
        "del",
        "ins",
        "details",
        "summary",
        "dl",
        "dt",
        "dd",
        "section",
        "article",
        "kbd",
        "samp",
        "var",
    }

    def allow_attribute(tag: str, name: str, value: str) -> bool:
        if name in {"id", "class", "title", "style", "role", "aria-label"}:
            return True
        if tag == "a" and name in {"href", "name"}:
            return not value.lower().startswith("data:")
        if tag == "img" and name in {"src", "alt", "width", "height"}:
            return not value.lower().startswith("data:") or value.lower().startswith("data:image/")
        return name in {"colspan", "rowspan", "scope", "align", "start", "reversed", "open"}

    return str(
        bleach.clean(
            str(parsed),
            tags=tags,
            attributes=allow_attribute,
            protocols=["http", "https", "mailto", "data", "attachment"],
            css_sanitizer=CSSSanitizer(),
            strip=True,
        )
    )


def text(value: object) -> str:
    return "".join(value) if isinstance(value, list) else str(value)


def prepare_outputs(nb: NotebookNode, notes: list[str], trusted_html: bool = False) -> None:
    """標準の静的出力がない場合も、内容を黙って落とさない。"""
    widgets = custom = 0
    for cell in nb.cells:
        if cell.cell_type == "raw":
            raw_html = cell.metadata.get("raw_mimetype") == "text/html"
            cell.cell_type = "markdown"
            cell.source = cell.source if raw_html else "<pre>" + html.escape(cell.source) + "</pre>"
        for output in cell.get("outputs", []):
            data = output.get("data", {})
            # External filename hints can override embedded MIME data in nbconvert.
            # Use the saved data, and never read paths merely supplied in metadata.
            output.get("metadata", {}).pop("filenames", None)
            output.pop("svg_filename", None)
            if not trusted_html:
                output.get("metadata", {}).get("text/html", {}).pop("isolated", None)
                if "text/html" in data:
                    original = text(data["text/html"])
                    cleaned = clean_html(original)
                    visible = BeautifulSoup(cleaned, "html.parser")
                    if not visible.get_text(strip=True) and not visible.find(
                        ["img", "table", "hr"]
                    ):
                        del data["text/html"]
                        notes.append("安全な静的表示がないHTML出力を代替表示にしました。")
                        if not data:
                            data["text/plain"] = "[スクリプト等に依存するHTML出力を省略]"
                    else:
                        data["text/html"] = cleaned
            if WIDGET_MIME in data:
                widgets += 1
            if not data or any(mime in data for mime in STATIC_MIMES):
                continue
            browser_image = next(
                (m for m in ("image/gif", "image/webp", "image/avif", "image/bmp") if m in data),
                None,
            )
            if browser_image:
                encoded = text(data[browser_image]).replace("\n", "")
                data["text/html"] = (
                    '<img alt="Notebookの画像出力" src="data:'
                    + browser_image
                    + ";base64,"
                    + html.escape(encoded, quote=True)
                    + '">'
                )
                continue
            custom += 1
            kinds = ", ".join(data)
            payload = json.dumps(data, ensure_ascii=False, indent=2)
            data["text/html"] = (
                '<details class="output-note"><summary>静的表示用データがない出力: '
                + html.escape(kinds)
                + "</summary><pre>"
                + html.escape(payload)
                + "</pre></details>"
            )
    if widgets:
        notes.append(
            f"Widget出力 {widgets}件: 対話機能は再現せず、保存された静的表示またはデータを掲載。"
        )
    if custom:
        notes.append(f"独自形式の出力 {custom}件をデータ表示に置き換えました。")


def add_code_controls(
    soup: BeautifulSoup, nb: NotebookNode, collapsed: bool = False, hide: bool = False
) -> None:
    """コードセルへ開閉・コピー操作を追加する。hideなら入力コードだけを除去する。"""
    cells = [c for c in nb.cells if c.cell_type == "code"]
    nodes = soup.select("div.cell.code_cell")
    if len(nodes) != len(cells):
        raise ValueError(
            "NotebookとHTMLのコードセル数が一致しません。nbconvertの版を確認してください。"
        )
    language = str(nb.metadata.get("language_info", {}).get("name", "Code"))
    for index, (node, cell) in enumerate(zip(nodes, cells), 1):
        classes = node.get_attribute_list("class")
        classes.append("code-cell")
        node["class"] = classes
        input_node = node.find("div", class_="input", recursive=False)
        if input_node is None:
            continue
        if hide:
            input_node.decompose()
            continue
        details = soup.new_tag("details", attrs={"class": "code-details"})
        if not collapsed:
            details["open"] = ""
        summary = soup.new_tag("summary")
        label = soup.new_tag("span")
        execution = cell.get("execution_count")
        state = "未実行" if execution is None else f"In [{execution}]"
        label.string = f"{language} · セル {index:02} · {state}"
        summary.append(label)
        hint = soup.new_tag("span", attrs={"class": "fold-hint"})
        hint.string = "開く / 閉じる"
        summary.append(hint)
        details.append(summary)
        button = soup.new_tag("button", attrs={"class": "copy-button", "type": "button"})
        button.string = "コピー"
        details.append(button)
        input_node.replace_with(details)
        details.append(input_node)


def make_toc(soup: BeautifulSoup, title: str, depth: int) -> str:
    """見出しIDを一意にし、既存アンカーを保ちながら目次HTMLを生成する。"""
    # nbconvertが作る既存のアンカーを保ち、重複だけを一意にする。
    for anchor in soup.select("a.anchor-link"):
        anchor.decompose()
    headings = soup.select(
        ".text_cell_render h1, .text_cell_render h2, .text_cell_render h3, "
        ".text_cell_render h4, .text_cell_render h5, .text_cell_render h6"
    )
    for heading in headings:
        if heading.get("id"):
            heading["id"] = unquote(str(heading["id"]))
    # 文書タイトルと同じ最初のH1は本文で重複させない。リンク先は残す。
    first_h1 = next((h for h in headings if h.name == "h1"), None)
    if first_h1 and first_h1.get_text(" ", strip=True) == title:
        first_h1.name = "span"
        first_h1.clear()
        headings.remove(first_h1)
    heading_ids = {id(h) for h in headings}
    used = {str(t["id"]) for t in soup.select("[id]") if id(t) not in heading_ids}
    entries = []
    for index, h in enumerate(headings, 1):
        base = str(h.get("id", f"section-{index}")) or f"section-{index}"
        ident, suffix = base, 2
        while ident in used:
            ident = f"{base}-{suffix}"
            suffix += 1
        used.add(ident)
        h["id"] = ident
        level = int(h.name[1:])
        if level <= depth:
            h["data-toc-heading"] = ""
            entries.append((ident, h.get_text(" ", strip=True), level))
    min_level = min((e[2] for e in entries), default=1)
    return "".join(
        f'<a class="nav-depth-{min(level - min_level, 2)}" href="#{quote(ident, safe="-_.~")}">'
        f"{html.escape(label)}</a>"
        for ident, label, level in entries
    )
