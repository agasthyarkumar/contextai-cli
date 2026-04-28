import os
from pathlib import Path
from typing import List, Set

# Extensions we actively want to index
CODE_EXTENSIONS: Set[str] = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs",
    ".java", ".cpp", ".c", ".h", ".rb", ".php", ".swift",
    ".kt", ".cs", ".sh", ".bash", ".zsh",
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".json", ".md", ".html", ".css", ".scss", ".sql",
}

DEFAULT_IGNORE_DIRS: Set[str] = {
    "node_modules", ".git", "build", "dist", "__pycache__",
    ".venv", "venv", "env", ".tox", ".cache", "tmp", "temp",
    ".next", ".nuxt", "coverage", ".nyc_output",
}

DEFAULT_IGNORE_EXTENSIONS: Set[str] = {
    ".pyc", ".pyo", ".pyd", ".so", ".dylib", ".dll", ".exe", ".bin",
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".ico",
    ".mp4", ".mp3", ".zip", ".tar", ".gz", ".lock", ".sum",
}


def collect_files(
    root: Path,
    ignore_dirs: Set[str] = None,
    ignore_extensions: Set[str] = None,
    max_size_kb: int = 100,
) -> List[Path]:
    """Walk the project tree and return indexable code files."""
    ignore_dirs = ignore_dirs or DEFAULT_IGNORE_DIRS
    ignore_extensions = ignore_extensions or DEFAULT_IGNORE_EXTENSIONS
    max_bytes = max_size_kb * 1024
    collected: List[Path] = []

    for dirpath, dirnames, filenames in os.walk(root):
        # Prune ignored dirs in-place so os.walk skips their subtrees
        dirnames[:] = [
            d for d in dirnames
            if d not in ignore_dirs and not d.startswith(".")
        ]

        for name in filenames:
            p = Path(dirpath) / name
            ext = p.suffix.lower()
            if ext in ignore_extensions:
                continue
            if ext not in CODE_EXTENSIONS:
                continue
            try:
                if p.stat().st_size > max_bytes:
                    continue
            except OSError:
                continue
            collected.append(p)

    return sorted(collected)


def read_file_safe(filepath: Path, max_size_kb: int = 100) -> str:
    """Read a file up to the size limit; truncate gracefully on overflow."""
    max_bytes = max_size_kb * 1024
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as fh:
            content = fh.read(max_bytes)
        if len(content) == max_bytes:
            content += "\n... [file truncated — too large]"
        return content
    except OSError:
        return ""


def filter_to_existing(rel_paths: List[str], root: Path) -> List[Path]:
    """Convert relative path strings to absolute Paths, keeping only real files."""
    result: List[Path] = []
    for rel in rel_paths:
        p = root / rel
        if p.exists() and p.is_file():
            result.append(p)
    return result
