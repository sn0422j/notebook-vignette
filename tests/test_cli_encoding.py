"""UTF-8以外の出力先でも、CLIの表示とJSON出力が成立することを確認する。"""

import json
import os
import subprocess
import sys

import nbformat
import pytest


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(PYTHONIOENCODING="cp1252:strict", PYTHONUTF8="0")
    return subprocess.run(
        [sys.executable, "-m", "notebook_vignette", *arguments],
        env=environment,
        capture_output=True,
        encoding="cp1252",
        timeout=30,
        check=False,
    )


@pytest.mark.parametrize("json_output", [False, True])
def test_cli_render_with_legacy_output_encoding(notebook, tmp_path, json_output):
    source = notebook([nbformat.v4.new_markdown_cell("# 日本語 😀\n\n$x^2$")], name="日本語.ipynb")
    output = tmp_path / "report.html"
    arguments = [str(source), "-o", str(output), "--mathjax", "none"]
    if json_output:
        arguments.append("--json")
    result = run_cli(*arguments)

    assert result.returncode == 0, result.stderr
    assert "日本語 😀" in output.read_text(encoding="utf-8")
    if json_output:
        rows = json.loads(result.stdout)
        assert len(rows) == 1
        assert rows[0]["ok"] is True
        assert rows[0]["title"] == "日本語 😀"
        assert rows[0]["source"] == str(source.resolve())
        assert any("数式" in note for note in rows[0]["notes"])
    else:
        assert "report.html" in result.stdout
        assert result.stderr  # MathJax無効の注意事項も出力できる。


def test_cli_help_with_legacy_output_encoding():
    result = run_cli("--help")
    assert result.returncode == 0, result.stderr
    assert "--theme" in result.stdout


@pytest.mark.parametrize("arguments", [[], ["--unknown-option"], ["存在しない.ipynb"]])
def test_cli_errors_with_legacy_output_encoding(arguments):
    result = run_cli(*arguments)
    assert result.returncode == 2
    assert result.stderr
    assert "Traceback" not in result.stderr
