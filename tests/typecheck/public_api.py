"""静的検査専用。公開APIで設定・色・戻り値の型が維持されることを確認する。"""

from pathlib import Path
from typing import assert_type

from notebook_vignette import (
    AppConfig,
    ColorOverrides,
    NotebookRenderer,
    RenderConfig,
    ThemeConfig,
    render_notebook,
)
from notebook_vignette.config import load_config, parse_overrides
from notebook_vignette.models import ConfigOverrides, ResolvedTheme
from notebook_vignette.result import RenderStats
from notebook_vignette.themes import resolve_theme


def type_contract(path: Path) -> None:
    config = AppConfig(
        render=RenderConfig(font=path, mathjax="none"),
        theme=ThemeConfig(name="dark", colors=ColorOverrides(accent="#abcdef")),
    )
    assert_type(load_config(None), AppConfig)
    assert_type(parse_overrides([]), ConfigOverrides)
    assert_type(resolve_theme(config.theme), ResolvedTheme)
    assert_type(resolve_theme(config.theme).colors.accent, str)
    assert_type(render_notebook(path, config=config), RenderStats)
    assert_type(NotebookRenderer(config).render(path), RenderStats)


def rejected_values() -> None:
    # If these mistakes become accepted, warn_unused_ignores makes mypy fail.
    RenderConfig(toc_depth="3")  # type: ignore[arg-type]
    RenderConfig(font="font.ttf")  # type: ignore[arg-type]
    ThemeConfig(name="unknown")  # type: ignore[arg-type]
    ColorOverrides(acccent="#abcdef")  # type: ignore[call-arg]
