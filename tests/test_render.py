import base64
import json

import nbformat as nbf
import pytest
from bs4 import BeautifulSoup
from conftest import PNG, SVG

from notebook_vignette import render_notebook


def read_page(stats):
    from pathlib import Path

    return BeautifulSoup(Path(stats["output"]).read_text(encoding="utf-8"), "html.parser")


def display(data, **kwargs):
    return nbf.v4.new_output("display_data", data=data, **kwargs)


def test_empty_and_source_unchanged(notebook):
    path = notebook()
    before = path.read_bytes()
    stats = render_notebook(path, mathjax="none", date="")
    assert stats["code_cells"] == 0
    assert path.read_bytes() == before
    assert read_page(stats).title.string == "sample"


def test_code_never_executes_and_errors_display(notebook):
    cell = nbf.v4.new_code_cell(
        "raise RuntimeError('DO NOT RUN')",
        outputs=[
            nbf.v4.new_output("stream", name="stdout", text="保存された出力\n"),
            nbf.v4.new_output(
                "error", ename="ValueError", evalue="bad", traceback=["ValueError: bad"]
            ),
        ],
    )
    stats = render_notebook(notebook([cell]), mathjax="none")
    page = read_page(stats)
    assert "DO NOT RUN" in page.get_text()
    assert "保存された出力" in page.get_text()
    assert "ValueError: bad" in page.get_text()
    assert stats["errors"] == stats["unexecuted_cells"] == 1


@pytest.mark.parametrize("option", ["collapse_code", "hide_code"])
def test_code_visibility(notebook, option):
    cell = nbf.v4.new_code_cell(
        "SECRET_INPUT", outputs=[nbf.v4.new_output("stream", name="stdout", text="VISIBLE_OUTPUT")]
    )
    page = read_page(render_notebook(notebook([cell]), **{option: True}))
    assert "VISIBLE_OUTPUT" in page.get_text()
    if option == "hide_code":
        assert "SECRET_INPUT" not in str(page)
    else:
        assert not page.select_one(".code-details").has_attr("open")


def test_toc_duplicates_japanese_title_and_links(notebook):
    cell = nbf.v4.new_markdown_cell(
        "# 日本語タイトル\n\n## 重複\n\n## 重複\n\n### 詳細\n\n[本文](#重複)"
    )
    page = read_page(render_notebook(notebook([cell]), toc_depth=2))
    assert page.title.string == "日本語タイトル"
    nav = page.select("nav a")
    assert len(nav) == 2
    assert len({a["href"] for a in nav}) == 2
    assert page.select_one("#重複") is not None


@pytest.mark.parametrize("theme", ["default", "dark", "paper"])
def test_themes(notebook, theme):
    stats = render_notebook(notebook([nbf.v4.new_markdown_cell("hello")]), theme={"name": theme})
    assert stats["theme"] == theme
    assert "--accent:" in read_page(stats).style.string


def test_inline_theme_then_api_override(notebook):
    path = notebook(
        metadata={"vignette": {"theme": {"name": "paper", "colors": {"accent": "#123456"}}}}
    )
    page = read_page(render_notebook(path, theme={"colors": {"accent": "#abcdef"}}))
    assert "--accent:#abcdef" in page.style.string
    assert "--background:#f4f0e7" in page.style.string


@pytest.mark.parametrize(
    "data,selector",
    [
        ({"image/png": PNG}, 'img[src^="data:image/png"]'),
        ({"image/jpeg": PNG}, 'img[src^="data:image/jpeg"]'),
        ({"image/svg+xml": SVG}, 'img[src^="data:image/svg+xml"]'),
        ({"image/gif": PNG}, 'img[src^="data:image/gif"]'),
        ({"image/webp": PNG}, 'img[src^="data:image/webp"]'),
        ({"text/html": "<table><tr><td>日本語</td></tr></table>"}, "table td"),
        ({"text/markdown": "**太字**"}, "strong"),
        ({"text/latex": r"$x^2$"}, ".output_latex"),
        ({"text/plain": "plain text"}, ".output_text pre"),
        ({"application/vnd.vendor+json": {"a": 1}}, "details.output-note"),
        ({"application/vnd.jupyter.widget-view+json": {"model_id": "abc"}}, "details.output-note"),
    ],
)
def test_saved_mime_routing(notebook, data, selector):
    path = notebook([nbf.v4.new_code_cell("", outputs=[display(data)])])
    page = read_page(render_notebook(path, mathjax="none"))
    assert page.select_one(selector) is not None


def test_html_sanitized_raw_markdown_and_output(notebook):
    attack = '<script>alert("UNSAFE_SCRIPT")</script><img src="x" onerror="alert(1)"><a href="javascript:alert(1)">link</a><p>KEEP</p>'
    raw = nbf.v4.new_raw_cell(attack, metadata={"raw_mimetype": "text/html"})
    code = nbf.v4.new_code_cell(
        "", outputs=[display({"text/html": attack}, metadata={"text/html": {"isolated": True}})]
    )
    page = read_page(
        render_notebook(notebook([raw, nbf.v4.new_markdown_cell(attack), code]), mathjax="none")
    )
    assert "UNSAFE_SCRIPT" not in str(page)
    assert "onerror" not in str(page)
    assert "javascript:" not in str(page)
    assert page.find("iframe") is None
    assert page.get_text().count("KEEP") == 3


def test_trusted_html_is_explicit(notebook):
    path = notebook(
        [
            nbf.v4.new_code_cell(
                "", outputs=[display({"text/html": "<script>window.TEST=1</script><p>chart</p>"})]
            )
        ]
    )
    page = read_page(render_notebook(path, trusted_html=True))
    assert any("window.TEST=1" in (s.string or "") for s in page.find_all("script"))


def test_script_only_html_falls_back(notebook):
    path = notebook(
        [
            nbf.v4.new_code_cell(
                "",
                outputs=[
                    display({"text/html": "<script>bad()</script>", "text/plain": "fallback"})
                ],
            )
        ]
    )
    page = read_page(render_notebook(path))
    assert "fallback" in page.get_text()


def test_raw_plain_text_escaped(notebook):
    page = read_page(render_notebook(notebook([nbf.v4.new_raw_cell("<b>literal</b>")])))
    assert "<b>literal</b>" in page.get_text()


def test_attachment_and_missing_attachment(notebook):
    cell = nbf.v4.new_markdown_cell(
        "![png](attachment:image.png)\n\n![svg](attachment:plot.svg)\n\n![missing](attachment:lost.png)",
        attachments={"image.png": {"image/png": PNG}, "plot.svg": {"image/svg+xml": SVG}},
    )
    stats = render_notebook(notebook([cell]))
    page = read_page(stats)
    assert page.select_one('img[src^="data:image/png"]')
    svg = page.select_one('img[src^="data:image/svg+xml"]')["src"]
    assert "<svg" in base64.b64decode(svg.split(",", 1)[1]).decode()
    assert any("lost.png" in note for note in stats["notes"])


def test_local_image_and_link_rebase(notebook, tmp_path):
    path = notebook(
        [nbf.v4.new_markdown_cell("![local](pixel.png)\n\n[CSV](data.csv#table)")],
        name="input/sample.ipynb",
    )
    (path.parent / "pixel.png").write_bytes(base64.b64decode(PNG))
    stats = render_notebook(path, tmp_path / "output" / "report.html")
    page = read_page(stats)
    assert stats["embedded_local_images"] == 1
    assert page.select_one('a[href="../input/data.csv#table"]')


def test_outside_image_default_denied_and_opt_in(notebook, tmp_path):
    path = notebook(
        [nbf.v4.new_markdown_cell("![outside](../private.png)")], name="input/sample.ipynb"
    )
    (tmp_path / "private.png").write_bytes(base64.b64decode(PNG))
    stats = render_notebook(path)
    assert stats["embedded_local_images"] == 0
    assert not read_page(stats).find("img").has_attr("src")
    allowed = render_notebook(path, overwrite=True, allow_outside_assets=True)
    assert allowed["embedded_local_images"] == 1


def test_symlink_image_boundary(notebook, tmp_path):
    path = notebook([nbf.v4.new_markdown_cell("![outside](link.png)")], name="input/sample.ipynb")
    secret = tmp_path / "outside.png"
    secret.write_bytes(base64.b64decode(PNG))
    try:
        (path.parent / "link.png").symlink_to(secret)
    except OSError:
        pytest.skip("Symlinks unavailable for this account")
    assert render_notebook(path)["embedded_local_images"] == 0


def test_existing_output_protected_and_failed_conversion_preserves(notebook, monkeypatch):
    path = notebook()
    destination = path.with_suffix(".html")
    destination.write_text("ORIGINAL")
    with pytest.raises(FileExistsError):
        render_notebook(path)
    monkeypatch.setattr(
        "notebook_vignette.content.HTMLExporter.from_notebook_node",
        lambda *a, **k: (_ for _ in ()).throw(ValueError("failed")),
    )
    with pytest.raises(ValueError, match="failed"):
        render_notebook(path, overwrite=True)
    assert destination.read_text() == "ORIGINAL"


def test_math_auto_none_and_date_escaping(notebook):
    path = notebook([nbf.v4.new_markdown_cell(r"## 数式" + "\n\n" + r"$x^2$ / $$y=2$$")])
    page = read_page(render_notebook(path, date="<img src=x>"))
    assert page.select_one('script[src*="mathjax@3.2.2"]')
    assert page.select_one(".date").get_text() == "HTML生成 <img src=x>"
    disabled = read_page(render_notebook(path, mathjax="none", overwrite=True))
    assert not disabled.select("script[src]")


def test_kernel_language_and_legacy_v3(notebook, tmp_path):
    path = notebook([nbf.v4.new_code_cell("x <- 1")], metadata={"language_info": {"name": "R"}})
    assert "R · セル" in read_page(render_notebook(path)).get_text()
    legacy = tmp_path / "legacy.ipynb"
    legacy.write_text(
        json.dumps(
            {
                "nbformat": 3,
                "nbformat_minor": 0,
                "metadata": {},
                "worksheets": [
                    {"cells": [{"cell_type": "markdown", "metadata": {}, "source": "# Legacy"}]}
                ],
            }
        )
    )
    assert render_notebook(legacy)["title"] == "Legacy"
