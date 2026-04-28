import subprocess
from pathlib import Path
from typing import List


def _run(cmd: List[str], cwd: Path) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    except FileNotFoundError:
        raise RuntimeError(
            "git not found. Make sure git is installed and available in your PATH."
        )


def is_git_repo(path: Path = None) -> bool:
    path = path or Path.cwd()
    try:
        return _run(["git", "rev-parse", "--git-dir"], path).returncode == 0
    except RuntimeError:
        return False


def get_repo_name(path: Path = None) -> str:
    path = path or Path.cwd()
    result = _run(["git", "remote", "get-url", "origin"], path)
    if result.returncode == 0:
        url = result.stdout.strip()
        return url.rstrip("/").split("/")[-1].removesuffix(".git")
    return path.name


def get_changed_files(path: Path = None) -> List[str]:
    """Return files changed in the most recent commit, falling back to all tracked files."""
    path = path or Path.cwd()

    for cmd in (
        ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
        ["git", "ls-files"],
    ):
        result = _run(cmd, path)
        if result.returncode == 0 and result.stdout.strip():
            return [f for f in result.stdout.strip().splitlines() if f.strip()]

    return []


def get_diff_content(path: Path = None, files: List[str] = None) -> str:
    """Return git diff text, hard-capped to avoid blowing the prompt budget."""
    path = path or Path.cwd()
    cmd = ["git", "diff", "HEAD~1", "HEAD"]
    if files:
        cmd += ["--"] + files
    result = _run(cmd, path)
    return result.stdout[:4000]
