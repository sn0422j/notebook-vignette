from dataclasses import FrozenInstanceError
from pathlib import Path

import nbformat
import pytest

from notebook_vignette import (
    AppConfig,
    ColorOverrides,
    NotebookRenderer,
    RenderConfig,
    ThemeConfig,
    render_notebook,
)
from notebook_vignette.config import load_config, parse_overrides, parse_theme_config
from notebook_vignette.models import ConfigOverrides, RenderOverrides
from notebook_vignette.themes import resolve_theme


def test_default_config_and_theme_are_typed():
    config = load_config(None)
    assert isinstance(config, AppConfig)
    assert isinstance(config.render, RenderConfig)
    assert isinstance(config.theme.colors, ColorOverrides)
    assert resolve_theme(config.theme).colors.accent == "#087f8c"


def test_nested_settings_cannot_be_mutated():
    config = AppConfig(theme=ThemeConfig(colors=ColorOverrides(accent="#abcdef")))
    with pytest.raises(FrozenInstanceError):
        config.render.hide_code = True
    with pytest.raises(FrozenInstanceError):
        config.theme.colors.accent = "#123456"
    exported = config.theme.colors.values()
    exported["accent"] = "#123456"
    assert config.theme.colors.accent == "#abcdef"


def test_false_and_empty_string_override_without_mutating_original():
    original = AppConfig(render=RenderConfig(hide_code=True, date="2000.01.01"))
    updated = original.apply(parse_overrides(["render.hide_code=false", 'render.date=""']))
    assert updated.render.hide_code is False
    assert updated.render.date == ""
    assert original.render.hide_code is True
    assert original.render.date == "2000.01.01"


def test_theme_overlay_preserves_individual_color_precedence():
    lower = ThemeConfig(name="paper", colors=ColorOverrides(accent="#111111", ink="#222222"))
    higher = ThemeConfig(name="dark", colors=ColorOverrides(accent="#333333"))
    theme = resolve_theme(lower.overlay(higher))
    assert theme.name == "dark"
    assert theme.colors.accent == "#333333"
    assert theme.colors.ink == "#222222"
    assert theme.colors.background == "#0e1822"


@pytest.mark.parametrize(
    "factory",
    [
        lambda: RenderConfig(toc_depth=True),
        lambda: RenderConfig(hide_code="false"),
        lambda: RenderConfig(font="font.woff2"),
        lambda: ThemeConfig(line_height=True),
        lambda: ThemeConfig(colors={"accent": "#abcdef"}),
        lambda: ColorOverrides(accent="red;}</style>"),
    ],
)
def test_invalid_direct_python_values_are_rejected(factory):
    with pytest.raises((TypeError, ValueError)):
        factory()


def test_combined_config_is_validated_after_overrides():
    config = AppConfig(render=RenderConfig(hide_code=True))
    with pytest.raises(ValueError, match="併用"):
        config.apply(ConfigOverrides(render=RenderOverrides(collapse_code=True)))


def test_toml_path_is_path_object(tmp_path):
    path = tmp_path / "vignette.toml"
    path.write_text('[render]\nfont="assets/font.woff2"\n')
    assert load_config(path).render.font == tmp_path / "assets/font.woff2"
    assert isinstance(load_config(path).render.font, Path)


def test_unknown_nested_color_fails_at_boundary():
    with pytest.raises(ValueError, match="acccent"):
        parse_theme_config({"colors": {"acccent": "#fff"}})


def test_typed_and_legacy_api_generate_identical_html(notebook, tmp_path):
    source = notebook([nbformat.v4.new_markdown_cell("# Typed configuration")])
    typed = tmp_path / "typed.html"
    legacy = tmp_path / "legacy.html"
    config = AppConfig(
        render=RenderConfig(collapse_code=True, mathjax="none", date=""),
        theme=ThemeConfig(name="dark", colors=ColorOverrides(accent="#aabbcc")),
    )
    render_notebook(source, typed, config=config)
    render_notebook(
        source,
        legacy,
        collapse_code=True,
        mathjax="none",
        date="",
        theme={"name": "dark", "colors": {"accent": "#aabbcc"}},
    )
    assert typed.read_text(encoding="utf-8") == legacy.read_text(encoding="utf-8")


def test_renderer_reuse_does_not_leak_notes_or_notebook_theme(notebook, tmp_path):
    renderer = NotebookRenderer(AppConfig(render=RenderConfig(mathjax="none")))
    first = notebook(
        [nbformat.v4.new_markdown_cell("$x^2$")],
        name="first.ipynb",
        metadata={"vignette": {"theme": {"name": "dark"}}},
    )
    second = notebook(name="second.ipynb")
    one = renderer.render(first, tmp_path / "one.html")
    two = renderer.render(second, tmp_path / "two.html")
    assert one["theme"] == "dark"
    assert one["notes"]
    assert two["theme"] == "default"
    assert two["notes"] == []


def test_explicit_keyword_overrides_typed_config(notebook, tmp_path):
    source = notebook([nbformat.v4.new_code_cell("VISIBLE_INPUT")])
    config = AppConfig(render=RenderConfig(hide_code=True))
    output = tmp_path / "report.html"
    render_notebook(source, output, config=config, hide_code=False)
    assert "VISIBLE_INPUT" in output.read_text(encoding="utf-8")
    assert config.render.hide_code is True
