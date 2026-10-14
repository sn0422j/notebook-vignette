from pathlib import Path

import nbformat
import pytest

PNG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jC1sAAAAASUVORK5CYII="
SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="160" height="60"><rect width="160" height="60" fill="#087f8c"/></svg>'


@pytest.fixture
def notebook(tmp_path):
    def write(cells=None, metadata=None, name="sample.ipynb") -> Path:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        nb = nbformat.v4.new_notebook(cells=cells or [], metadata=metadata or {})
        nbformat.write(nb, path)
        return path

    return write
