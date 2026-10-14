"""画像・数式・フォントの参照を処理する。外部URLのダウンロードは行わない。"""

from __future__ import annotations

import base64
import html
import json
import mimetypes
import os
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import SplitResult, quote, unquote, urlsplit

from bs4 import BeautifulSoup

from .models import MathJaxMode, RenderConfig

MATHJAX_URL = "https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/tex-svg-full.js"


@dataclass(frozen=True, slots=True)
class PageAssets:
    """HTMLページに埋め込む補助データと画像処理結果。"""

    math_html: str
    font_css: str
    font_license_html: str
    embedded_local_images: int


def prepare_assets(
    soup: BeautifulSoup, source: Path, destination: Path, config: RenderConfig, notes: list[str]
) -> PageAssets:
    """画像・リンクを更新し、数式とフォントの埋め込みデータをまとめて返す。"""
    embedded = embed_images_and_rebase_links(
        soup, source.parent, destination.parent, notes, config.allow_outside_assets
    )
    math_html = math_assets(soup, config.mathjax, config.mathjax_js, notes)
    font_css, license_html = font_assets(config.font, config.font_license)
    external = sum(
        str(node[attr]).startswith(("http://", "https://", "//"))
        for tag, attr in (("img", "src"), ("script", "src"), ("link", "href"), ("iframe", "src"))
        for node in soup.find_all(tag, attrs={attr: True})
    )
    if external:
        notes.append(f"本文に外部リソースへの参照が{external}件残っています。")
    if config.trusted_html:
        notes.append(
            "入力NotebookのHTML/JavaScriptを保持しています。対話型出力の動作は必要なライブラリ等に依存します。"
        )
    return PageAssets(math_html, font_css, license_html, embedded)


def local_path(src: str, directory: Path) -> Path | None:
    """ローカル参照だけを解決し、URLなどはNoneを返す。"""
    parsed = urlsplit(src)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    return (directory / unquote(parsed.path)).resolve()


def embed_images_and_rebase_links(
    soup: BeautifulSoup,
    directory: Path,
    output_directory: Path,
    notes: list[str],
    allow_outside: bool = False,
) -> int:
    """許可範囲内の画像を埋め込み、相対リンクを出力先基準へ変更する。"""
    embedded = 0
    for img in soup.find_all("img", src=True):
        src = str(img["src"])
        if src.startswith("data:"):
            continue
        path = local_path(src, directory)
        if path is None:
            if src.startswith("attachment:"):
                notes.append(f"添付画像を解決できません: {src}")
            continue
        if not allow_outside and not path.is_relative_to(directory):
            notes.append(f"Notebookのフォルダ外の画像を除外しました: {src}")
            img.attrs.pop("src", None)
            img.attrs.pop("srcset", None)
            img["alt"] = str(img.get("alt", "")) + " [フォルダ外の画像]"
            continue
        mime = mimetypes.guess_type(path.name)[0]
        if not path.is_file() or not mime or not mime.startswith("image/"):
            notes.append(f"画像を埋め込めません: {src}")
            img["src"] = relative_url(path, output_directory, urlsplit(src))
            continue
        img["src"] = f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")
        embedded += 1
        # srcsetが元パスを優先しないようにする。
        img.attrs.pop("srcset", None)
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"])
        if href.startswith("#"):
            continue
        path = local_path(href, directory)
        if path is not None:
            anchor["href"] = relative_url(path, output_directory, urlsplit(href))
    return embedded


def relative_url(path: Path, directory: Path, parsed: SplitResult) -> str:
    """クエリとフラグメントを保って出力先基準のURLを作成する。"""
    try:
        target = quote(Path(os.path.relpath(path, directory)).as_posix(), safe="/:")
    except ValueError:  # Windowsでドライブが違う場合
        target = path.as_uri()
    if parsed.query:
        target += "?" + parsed.query
    if parsed.fragment:
        target += "#" + parsed.fragment
    return target


def math_assets(
    soup: BeautifulSoup, mode: MathJaxMode, local_js: Path | None, notes: list[str]
) -> str:
    """数式設定に従うscript要素を生成する。CDNの取得はブラウザに委ねる。"""
    visible = " ".join(
        str(t)
        for t in soup.find_all(string=True)
        if not any(p.name in {"pre", "code", "script", "style"} for p in t.parents)
    )
    detected = bool(soup.select(".math, .output_latex, math")) or bool(
        re.search(r"(?<!\\)\$|\\\(|\\\[|\\begin\{", visible)
    )
    if mode == "none":
        if detected:
            notes.append("数式レンダリングは無効です。TeXをそのまま表示しています。")
        return ""
    if mode == "auto" and not detected:
        return ""
    configuration = {
        "tex": {
            "inlineMath": [["$", "$"], [r"\(", r"\)"]],
            "displayMath": [["$$", "$$"], [r"\[", r"\]"]],
            "processEscapes": True,
        },
        "svg": {"fontCache": "global"},
    }
    result = "<script>window.MathJax=" + json.dumps(configuration) + ";</script>"
    if local_js:
        source = local_js.expanduser().read_text(encoding="utf-8")
        source = re.sub(r"</script", r"<\/script", source, flags=re.I)
        result += "<script>" + source + "</script>"
        notes.append(
            "数式用MathJaxを埋め込み済み。追加のTeX拡張は外部参照を必要とする場合があります。"
        )
    else:
        result += f'<script defer src="{MATHJAX_URL}"></script>'
        notes.append("数式表示にはMathJaxの読み込みのためインターネット接続が必要です。")
    return result


def font_assets(font: Path | None, license_path: Path | None) -> tuple[str, str]:
    """フォントのCSSと、任意のライセンス表示用HTMLを生成する。"""
    if font is None:
        return "", ""
    path = font.expanduser()
    mime = {
        ".ttf": "font/ttf",
        ".otf": "font/otf",
        ".woff": "font/woff",
        ".woff2": "font/woff2",
    }.get(path.suffix.lower())
    if mime is None:
        raise ValueError("--font には .ttf / .otf / .woff / .woff2 を指定してください。")
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    style = (
        "@font-face{font-family:VignetteJP;src:url(data:"
        + mime
        + ";base64,"
        + data
        + ");font-display:swap}"
    )
    license_html = ""
    if license_path:
        license_html = (
            "<details><summary>埋め込みフォントのライセンス</summary><pre>"
            + html.escape(license_path.expanduser().read_text(encoding="utf-8"))
            + "</pre></details>"
        )
    return style, license_html
