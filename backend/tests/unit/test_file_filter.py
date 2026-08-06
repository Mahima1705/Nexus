from pathlib import Path

from app.repository_processor.file_filter import detect_language, is_binary_extension, iter_repository_files


def test_iter_repository_files_skips_ignored_directories(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hi')")
    (tmp_path / "node_modules" / "pkg").mkdir(parents=True)
    (tmp_path / "node_modules" / "pkg" / "index.js").write_text("module.exports = {}")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/main")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "main.cpython-311.pyc").write_bytes(b"\x00\x01")

    found = {str(rel).replace("\\", "/") for _abs, rel in iter_repository_files(tmp_path)}

    assert found == {"src/main.py"}


def test_detect_language_by_extension() -> None:
    assert detect_language(Path("app/main.py")) == "python"
    assert detect_language(Path("web/index.tsx")) == "typescript"
    assert detect_language(Path("Dockerfile")) == "dockerfile"
    assert detect_language(Path("README")) is None


def test_is_binary_extension() -> None:
    assert is_binary_extension(Path("logo.png")) is True
    assert is_binary_extension(Path("main.py")) is False
