import subprocess
from pathlib import Path
from typing import List


def _run(cmd: List[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)


def is_git_repo(path: Path = None) -> bool:
    path = path or Path.cwd()
    return _run(["git", "rev-parse", "--git-dir"], path).returncode == 0


def get_repo_name(path: Path = None) -> str:
    path = path or Path.cwd()
    result = _run(["git", "remote", "get-url", "origin"], path)
    if result.returncode == 0:
        url = result.stdout.strip()
        return url.rstrip("/").split("/")[-1].removesuffix(".git")
    return path.name


def get_current_commit_hash(path: Path = None) -> str:
    path = path or Path.cwd()
    result = _run(["git", "rev-parse", "HEAD"], path)
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def get_changed_files(path: Path = None) -> List[str]:
    """Return files changed in the most recent commit.

    Falls back to staged files (first commit) or all tracked files.
    """
    path = path or Path.cwd()

    # Normal case: diff against parent
    result = _run(["git", "diff", "--name-only", "HEAD~1", "HEAD"], path)
    if result.returncode == 0 and result.stdout.strip():
        return [f.strip() for f in result.stdout.strip().splitlines() if f.strip()]

    # First commit: list everything tracked
    result = _run(["git", "ls-files"], path)
    if result.returncode == 0 and result.stdout.strip():
        return [f.strip() for f in result.stdout.strip().splitlines() if f.strip()]

    return []


def get_diff_content(path: Path = None, files: List[str] = None) -> str:
    """Return git diff text, capped to avoid blowing the prompt budget."""
    path = path or Path.cwd()
    cmd = ["git", "diff", "HEAD~1", "HEAD"]
    if files:
        cmd += ["--"] + files
    result = _run(cmd, path)
    return result.stdout[:4000]  # hard cap — we only need a hint for the LLM
