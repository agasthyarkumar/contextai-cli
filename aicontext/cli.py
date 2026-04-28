"""Typer-based CLI entry point for aicontext."""

import shutil
import stat
from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(
    name="aicontext",
    help="Maintain a compressed, LLM-friendly context of your codebase.",
    no_args_is_help=True,
    add_completion=False,
)

# ── Git hook script installed by `aicontext init` ─────────────────────────────
_HOOK_SCRIPT = """\
#!/bin/sh
# Installed by aicontext — updates LLM context after every commit.
aicontext update
"""


# ── init ──────────────────────────────────────────────────────────────────────

@app.command()
def init(
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing config and git hook."
    ),
) -> None:
    """Set up .aicontext.env from the example file and install the git post-commit hook."""
    from .config import AICONTEXT_ENV_FILE

    repo = Path.cwd()

    # 1. Create .aicontext.env ──────────────────────────────────────────────
    example = repo / ".aicontext.env.example"
    env_file = repo / AICONTEXT_ENV_FILE

    if example.exists():
        if not env_file.exists() or force:
            shutil.copy(example, env_file)
            typer.echo(f"✓ Created {AICONTEXT_ENV_FILE} from .aicontext.env.example")
            typer.echo(f"  → Open {AICONTEXT_ENV_FILE} and set GROQ_API_KEY")
        else:
            typer.echo(f"  {AICONTEXT_ENV_FILE} already exists  (use --force to overwrite)")
    else:
        typer.echo("  .aicontext.env.example not found — skipping config creation")

    # 2. Install git post-commit hook ───────────────────────────────────────
    git_dir = repo / ".git"
    if not git_dir.is_dir():
        typer.echo("  Not a git repo — skipping hook install", err=True)
        return

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    hook_path = hooks_dir / "post-commit"

    if hook_path.exists() and not force:
        typer.echo("  post-commit hook already exists  (use --force to overwrite)")
    else:
        hook_path.write_text(_HOOK_SCRIPT, encoding="utf-8")
        # Make executable
        mode = hook_path.stat().st_mode
        hook_path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        typer.echo("✓ Installed git post-commit hook")

    typer.echo("\nAll done! Run 'aicontext update --scan' to generate your first context.")


# ── update ─────────────────────────────────────────────────────────────────────

@app.command()
def update(
    scan: bool = typer.Option(
        False, "--scan", "-s",
        help="Full project scan instead of diff-only incremental update.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show progress details."),
) -> None:
    """Update context.json/context.md based on the latest git changes."""
    from .orchestrator import run_update, run_full_scan

    typer.echo("Updating context…")
    try:
        if scan:
            msg = run_full_scan(verbose=verbose)
        else:
            msg = run_update(verbose=verbose)
        typer.echo(f"✓ {msg}")
    except RuntimeError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)


# ── watch ──────────────────────────────────────────────────────────────────────

@app.command()
def watch(
    debounce: int = typer.Option(
        20, "--debounce", "-d",
        help="Seconds to wait after a change before re-running update.",
    ),
) -> None:
    """Watch for file changes and auto-update context (requires watchdog)."""
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        typer.echo(
            "watchdog is not installed.\n"
            "Run: pip install watchdog",
            err=True,
        )
        raise typer.Exit(code=1)

    import time
    from .orchestrator import run_update

    IGNORE_NAMES = {"context.json", "context.md"}

    class _Handler(FileSystemEventHandler):
        def __init__(self):
            self._last = 0.0

        def on_modified(self, event):
            if event.is_directory:
                return
            name = Path(event.src_path).name
            if name in IGNORE_NAMES:
                return
            now = time.time()
            if now - self._last < debounce:
                return
            self._last = now
            typer.echo(f"  Change: {event.src_path}")
            try:
                typer.echo(f"  ✓ {run_update()}")
            except Exception as exc:
                typer.echo(f"  Error: {exc}", err=True)

    observer = Observer()
    observer.schedule(_Handler(), path=".", recursive=True)
    observer.start()
    typer.echo(f"Watching… (debounce={debounce}s)  Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    typer.echo("Stopped.")


# ── show ───────────────────────────────────────────────────────────────────────

@app.command()
def show(
    fmt: str = typer.Option("md", "--format", "-f", help="Output format: md or json."),
) -> None:
    """Print the current context to stdout."""
    from .config import load_config

    repo = Path.cwd()
    config = load_config()

    if fmt == "json":
        target = repo / config["context_file"]
    else:
        target = repo / config["context_md_file"]

    if not target.exists():
        typer.echo(
            f"'{target.name}' not found. Run 'aicontext update --scan' first.",
            err=True,
        )
        raise typer.Exit(code=1)

    typer.echo(target.read_text(encoding="utf-8"))


# ── clean ──────────────────────────────────────────────────────────────────────

@app.command()
def clean(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
    all_files: bool = typer.Option(
        False, "--all", "-a",
        help="Also remove .aicontext.env and the git post-commit hook.",
    ),
) -> None:
    """Remove context.json and context.md (and optionally config + git hook)."""
    from .config import load_config, AICONTEXT_ENV_FILE

    repo = Path.cwd()
    config = load_config()

    targets = [
        repo / config["context_file"],
        repo / config["context_md_file"],
    ]
    hook_path = repo / ".git" / "hooks" / "post-commit"

    if all_files:
        targets.append(repo / AICONTEXT_ENV_FILE)

    # List what will actually be removed
    existing = [p for p in targets if p.exists()]
    hook_exists = all_files and hook_path.exists()

    if not existing and not hook_exists:
        typer.echo("Nothing to remove — no aicontext files found.")
        return

    typer.echo("Will remove:")
    for p in existing:
        typer.echo(f"  {p.relative_to(repo)}")
    if hook_exists:
        typer.echo(f"  .git/hooks/post-commit")

    if not yes:
        typer.confirm("\nProceed?", abort=True)

    for p in existing:
        p.unlink()
        typer.echo(f"  ✓ Removed {p.relative_to(repo)}")

    if hook_exists:
        hook_path.unlink()
        typer.echo("  ✓ Removed .git/hooks/post-commit")

    typer.echo("Done.")


# ── Aicontext's own source footprint in a user's project ──────────────────────
# These are the files/dirs that aicontext adds to a project when installed.
# README.md is intentionally excluded — it may belong to the host project.
_SOURCE_DIRS = ["aicontext", "scripts"]
_SOURCE_FILES = ["setup.py", "requirements.txt", ".aicontext.env.example", "USER_MANUAL.md"]

# Fingerprint: if this file exists inside the package, we're running inside
# the aicontext source repo itself — refuse destructive operations.
def _is_aicontext_source_repo(repo: Path) -> bool:
    """Return True if cwd is the aicontext development repo itself."""
    return (repo / "aicontext" / "cli.py").exists() and (repo / "aicontext" / "orchestrator.py").exists()


def _guard_source_repo(repo: Path) -> None:
    if _is_aicontext_source_repo(repo):
        typer.echo(
            "Error: This command cannot be run inside the aicontext source repo.\n"
            "\n"
            "  'ignore' and 'delete' are meant to remove aicontext from a HOST\n"
            "  project you installed it into (e.g. your Django app, Node API, etc.).\n"
            "\n"
            "  Running it here would delete the aicontext tool itself.",
            err=True,
        )
        raise typer.Exit(code=1)


# ── ignore ─────────────────────────────────────────────────────────────────────

@app.command()
def ignore() -> None:
    """Add aicontext source files to .gitignore (keeps files on disk)."""
    repo = Path.cwd()
    _guard_source_repo(repo)
    gitignore_path = repo / ".gitignore"

    block = (
        "\n# ── aicontext source (added by aicontext ignore) ──\n"
        + "\n".join(_SOURCE_DIRS + _SOURCE_FILES)
        + "\n"
    )

    # Read existing content so we can skip if already present
    existing = gitignore_path.read_text(encoding="utf-8") if gitignore_path.exists() else ""

    already = [e for e in _SOURCE_DIRS + _SOURCE_FILES if e in existing]
    if already:
        typer.echo("These entries are already in .gitignore:")
        for e in already:
            typer.echo(f"  {e}")
        typer.echo("No changes made.")
        return

    with open(gitignore_path, "a", encoding="utf-8") as f:
        f.write(block)

    typer.echo("✓ Added to .gitignore:")
    for entry in _SOURCE_DIRS + _SOURCE_FILES:
        typer.echo(f"  {entry}")
    typer.echo(
        "\nSource files are still on disk — only hidden from git.\n"
        "Run 'aicontext delete' to remove them entirely."
    )


# ── delete ─────────────────────────────────────────────────────────────────────

@app.command()
def delete(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
) -> None:
    """Remove all aicontext source code and generated files from this project."""
    import shutil
    from .config import load_config, AICONTEXT_ENV_FILE

    repo = Path.cwd()
    _guard_source_repo(repo)
    config = load_config()

    # Collect everything aicontext put in the project
    targets_dirs = [repo / d for d in _SOURCE_DIRS]
    targets_files = [repo / f for f in _SOURCE_FILES] + [
        repo / config["context_file"],
        repo / config["context_md_file"],
        repo / AICONTEXT_ENV_FILE,
    ]
    hook_path = repo / ".git" / "hooks" / "post-commit"

    existing_dirs = [d for d in targets_dirs if d.exists()]
    existing_files = [f for f in targets_files if f.exists()]
    hook_exists = hook_path.exists()

    if not existing_dirs and not existing_files and not hook_exists:
        typer.echo("Nothing to delete — no aicontext files found.")
        return

    typer.echo("Will permanently delete:")
    for d in existing_dirs:
        typer.echo(f"  {d.relative_to(repo)}/  (directory)")
    for f in existing_files:
        typer.echo(f"  {f.relative_to(repo)}")
    if hook_exists:
        typer.echo("  .git/hooks/post-commit")

    typer.echo(
        "\nThis removes the aicontext tool from this project.\n"
        "Your project's own files are NOT touched."
    )

    if not yes:
        typer.confirm("\nProceed?", abort=True)

    for d in existing_dirs:
        shutil.rmtree(d)
        typer.echo(f"  ✓ Removed {d.relative_to(repo)}/")

    for f in existing_files:
        f.unlink()
        typer.echo(f"  ✓ Removed {f.relative_to(repo)}")

    if hook_exists:
        hook_path.unlink()
        typer.echo("  ✓ Removed .git/hooks/post-commit")

    typer.echo(
        "\nDone. aicontext has been fully removed from this project.\n"
        "To uninstall the CLI globally: pip uninstall aicontext"
    )


# ── entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    app()
