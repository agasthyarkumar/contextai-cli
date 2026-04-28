"""Core pipeline: detect changes → summarize → update context files."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import load_config
from .analyzers.git_diff import (
    get_changed_files,
    get_current_commit_hash,
    get_diff_content,
    get_repo_name,
    is_git_repo,
)
from .analyzers.file_collector import (
    collect_files,
    filter_to_existing,
    read_file_safe,
)
from .llm.prompt_builder import build_init_prompt, build_update_prompt
from .llm.summarizer import summarize
from .storage.context_writer import (
    load_context,
    merge_context,
    save_context,
    write_markdown,
)


def _stamp_changes(context: dict) -> None:
    """Ensure every recent_change entry has a timestamp."""
    now = datetime.now(timezone.utc).isoformat()
    for ch in context.get("recent_changes", []):
        ch.setdefault("timestamp", now)


def run_update(repo_path: Optional[Path] = None, verbose: bool = False) -> str:
    """Incremental update: only process files that changed since last commit."""
    repo_path = repo_path or Path.cwd()

    if not is_git_repo(repo_path):
        raise RuntimeError("Not a git repository. Run 'git init' first.")

    config = load_config()
    context_path = repo_path / config["context_file"]
    md_path = repo_path / config["context_md_file"]

    existing = load_context(context_path)
    project_name = existing.get("project_name") or get_repo_name(repo_path)

    # --- detect changes ---
    changed_rel = get_changed_files(repo_path)

    ignore_dirs = config["ignore_dirs"]
    ignore_exts = config["ignore_extensions"]

    # Filter to indexable files before deciding what to do
    changed_paths = filter_to_existing(changed_rel, repo_path)
    files_content: dict[str, str] = {}
    for p in changed_paths:
        if p.suffix.lower() in ignore_exts:
            continue
        if any(part in ignore_dirs for part in p.parts):
            continue
        rel = str(p.relative_to(repo_path))
        files_content[rel] = read_file_safe(p, config["max_file_size_kb"])

    # If no existing modules and git only sees a handful of committed files,
    # the project is likely freshly created with uncommitted files — fall back
    # to a full filesystem scan so nothing is missed.
    if not existing.get("modules") and len(files_content) < 3:
        if verbose:
            print(
                "  No prior context and few git-tracked files detected.\n"
                "  Falling back to full filesystem scan (same as --scan)."
            )
        return run_full_scan(repo_path=repo_path, verbose=verbose)

    if not changed_rel:
        return "No changes detected in the last commit."

    if not files_content:
        return "All changed files are binary/ignored — nothing to summarize."

    if verbose:
        print(f"  Detected {len(files_content)} indexable changed file(s): {list(files_content)}")

    diff = get_diff_content(repo_path, changed_rel)

    # --- call LLM ---
    if existing.get("modules"):
        prompt = build_update_prompt(existing, files_content, diff)
    else:
        prompt = build_init_prompt(files_content, project_name)

    if verbose:
        print(f"  Calling LLM ({config['provider']})…")

    new_context = summarize(prompt, config)
    new_context.setdefault("project_name", project_name)
    _stamp_changes(new_context)

    merged = merge_context(existing, new_context)
    save_context(merged, context_path)
    write_markdown(merged, md_path)

    n_changed = len(files_content)
    n_total = len(merged.get("modules", {}))
    return f"Updated {n_changed} module(s). Context covers {n_total} module(s) total."


def run_full_scan(repo_path: Optional[Path] = None, verbose: bool = False) -> str:
    """Full project scan — indexes all code files (used by `aicontext update --scan`)."""
    repo_path = repo_path or Path.cwd()
    config = load_config()
    context_path = repo_path / config["context_file"]
    md_path = repo_path / config["context_md_file"]

    project_name = get_repo_name(repo_path)
    all_files = collect_files(
        repo_path,
        ignore_dirs=config["ignore_dirs"],
        ignore_extensions=config["ignore_extensions"],
        max_size_kb=config["max_file_size_kb"],
    )

    # Cap the initial scan to avoid enormous prompts
    capped = all_files[:30]
    if verbose:
        print(f"  Scanning {len(capped)}/{len(all_files)} file(s)…")

    files_content = {
        str(p.relative_to(repo_path)): read_file_safe(p, config["max_file_size_kb"])
        for p in capped
    }

    if not files_content:
        return "No indexable code files found."

    prompt = build_init_prompt(files_content, project_name)

    if verbose:
        print(f"  Calling LLM ({config['provider']})…")

    new_context = summarize(prompt, config)
    new_context.setdefault("project_name", project_name)

    save_context(new_context, context_path)
    write_markdown(new_context, md_path)

    n = len(new_context.get("modules", {}))
    return f"Full scan complete. Indexed {n} module(s)."
