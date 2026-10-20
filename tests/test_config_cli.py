import json

import pytest

from notebook_vignette.cli import main
from notebook_vignette.config import (
    load_config,
    parse_overrides,
    parse_theme_config,
    validate_render,
)
from notebook_vignette.themes import resolve_theme


@pytest.mark.parametrize(
    "theme",
    [
        {"colors": {"acccent": "#fff"}},
        {"colors": {"accent": "red;}</style><script>bad()</script>"}},
        {"font_family": "url(https://example.test)"},
        {"font_size": "-12px"},
        {"line_height": True},
        {"name": "missing"},
        {"syntax_style": "made-up-style"},
        {"unknown": 1},
    ],
)
def test_invalid_themes(theme):
    with pytest.raises(ValueError):
        resolve_theme(parse_theme_config(theme))


@pytest.mark.parametrize(
    "render",
    [
        {"hide_code": "false"},
        {"toc_depth": True},
        {"toc_depth": 7},
        {"unknown": True},
        {"hide_code": True, "collapse_code": True},
    ],
)
def test_invalid_render(render):
    with pytest.raises(ValueError):
        validate_render(render)


def test_cli_settings_precedence(notebook, tmp_path, capsys):
    path = notebook(metadata={"vignette": {"theme": {"colors": {"accent": "#111111"}}}})
    config = tmp_path / "config.toml"
    config.write_text('[render]\nhide_code=true\n[theme.colors]\naccent="#222222"\n')
    assert (
        main(
            [
                str(path),
                "--config",
                str(config),
                "--theme",
                "dark",
                "--show-code",
                "--set",
                "theme.colors.accent=#333333",
                "--json",
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result[0]["theme"] == "dark"
    assert "--accent:#333333" in path.with_suffix(".html").read_text(encoding="utf-8")


def test_config_relative_assets(tmp_path):
    config = tmp_path / "theme.toml"
    config.write_text('[render]\nfont="assets/font.woff2"\n')
    assert load_config(config).render.font == tmp_path / "assets/font.woff2"


def test_inline_override_parsing():
    values = parse_overrides(
        ["theme.colors.accent=#abcdef", "render.hide_code=false", "theme.line_height=1.5"]
    )
    assert values.render.hide_code is False
    assert values.theme.line_height == 1.5


def test_batch_hierarchy_and_checkpoints(notebook, tmp_path, capsys):
    notebook(name="inputs/a.ipynb")
    notebook(name="inputs/sub/b.ipynb")
    notebook(name="inputs/.ipynb_checkpoints/skip.ipynb")
    assert (
        main(
            [
                str(tmp_path / "inputs"),
                "--recursive",
                "--output-dir",
                str(tmp_path / "out"),
                "--json",
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert len(result) == 2
    assert (tmp_path / "out/sub/b.html").exists()


def test_batch_collision_preflight(notebook, tmp_path):
    a = notebook(name="a/same.ipynb")
    b = notebook(name="b/same.ipynb")
    assert main([str(a), str(b), "--output-dir", str(tmp_path / "out")]) == 2
    assert not (tmp_path / "out").exists()


def test_batch_error_continues(notebook, tmp_path, capsys):
    bad = tmp_path / "broken.ipynb"
    bad.write_text("not JSON")
    good = notebook()
    assert main([str(bad), str(good), "--json"]) == 1
    results = json.loads(capsys.readouterr().out)
    assert [r["ok"] for r in results] == [False, True]


def test_glob_and_overwrite_protection(notebook, tmp_path):
    notebook()
    pattern = str(tmp_path / "*.ipynb")
    assert main([pattern]) == 0
    assert main([pattern]) == 2
    assert main([pattern, "--force"]) == 0


def test_config_cannot_be_overwritten(notebook, tmp_path):
    path = notebook()
    config = tmp_path / "settings.html"
    config.write_text('[render]\ntitle="valid TOML with unusual filename"')
    assert main([str(path), "--config", str(config), "-o", str(config), "--force"]) == 2
    assert config.read_text().startswith("[render]")


def test_unknown_cli_setting_rejected(notebook):
    assert main([str(notebook()), "--set", "render.typo=true"]) == 2
