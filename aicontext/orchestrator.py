"""Core pipeline: detect changes → summarize → update context files."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import load_config
from .analyzers.git_diff import get_changed_files, get_diff_content, get_repo_name, is_git_repo
from .analyzers.file_collector import collect_files, filter_to_existing, read_file_safe
from .llm.prompt_builder import build_init_prompt, build_update_prompt
from .llm.summarizer import summarize
from .storage.context_writer import load_context, merge_context, save_context, write_markdown


def _stamp_changes(context: dict) -> None:
    now = datetime.now(timezone.utc).isoformat()
    for ch in context.get("recent_changes", []):
        ch.setdefault("timestamp", now)


def _collect_changed_content(changed_rel, repo_path, config) -> dict:
    """Filter changed files to indexable ones and read their content."""
    ignore_dirs = config["ignore_dirs"]
    ignore_exts = config["ignore_extensions"]
    result = {}
    for p in filter_to_existing(changed_rel, repo_path):
        if p.suffix.lower() in ignore_exts:
            continue
        if any(part in ignore_dirs for part in p.parts):
            continue
        result[str(p.relative_to(repo_path))] = read_file_safe(p, config["max_file_size_kb"])
    return result


def _save(context: dict, context_path: Path, md_path: Path) -> None:
    save_context(context, context_path)
    write_markdown(context, md_path)


def run_update(repo_path: Optional[Path] = None, verbose: bool = False) -> str:
    """Incremental update: only process files changed since the last commit."""
    repo_path = repo_path or Path.cwd()

    if not is_git_repo(repo_path):
        raise RuntimeError("Not a git repository. Run 'git init' first.")

    config = load_config()
    context_path = repo_path / config["context_file"]
    md_path = repo_path / config["context_md_file"]

    existing = load_context(context_path)
    project_name = existing.get("project_name") or get_repo_name(repo_path)

    changed_rel = get_changed_files(repo_path)
    files_content = _collect_changed_content(changed_rel, repo_path, config)

    # No existing context + few git-tracked files = uninitialized project → full scan
    if not existing.get("modules") and len(files_content) < 3:
        if verbose:
            print("  No prior context and few git-tracked files — falling back to full scan.")
        return run_full_scan(repo_path=repo_path, verbose=verbose, _config=config)

    if not changed_rel:
        return "No changes detected in the last commit."
    if not files_content:
        return "All changed files are binary/ignored — nothing to summarize."

    if verbose:
        print(f"  {len(files_content)} indexable changed file(s): {list(files_content)}")
        print(f"  Calling LLM ({config['provider']})…")

    diff = get_diff_content(repo_path, changed_rel)
    prompt = (
        build_update_prompt(existing, files_content, diff)
        if existing.get("modules")
        else build_init_prompt(files_content, project_name)
    )

    new_context = summarize(prompt, config)
    new_context.setdefault("project_name", project_name)
    _stamp_changes(new_context)

    merged = merge_context(existing, new_context)
    _save(merged, context_path, md_path)

    return (
        f"Updated {len(files_content)} module(s). "
        f"Context covers {len(merged.get('modules', {}))} module(s) total."
    )


def run_full_scan(
    repo_path: Optional[Path] = None,
    verbose: bool = False,
    _config: Optional[dict] = None,   # injected by run_update to avoid a second load
) -> str:
    """Full filesystem scan — indexes all code files regardless of git state."""
    repo_path = repo_path or Path.cwd()
    config = _config or load_config()
    context_path = repo_path / config["context_file"]
    md_path = repo_path / config["context_md_file"]

    all_files = collect_files(
        repo_path,
        ignore_dirs=config["ignore_dirs"],
        ignore_extensions=config["ignore_extensions"],
        max_size_kb=config["max_file_size_kb"],
    )
    capped = all_files[:30]

    if verbose:
        print(f"  Scanning {len(capped)}/{len(all_files)} file(s)…")
        print(f"  Calling LLM ({config['provider']})…")

    files_content = {
        str(p.relative_to(repo_path)): read_file_safe(p, config["max_file_size_kb"])
        for p in capped
    }

    if not files_content:
        return "No indexable code files found."

    new_context = summarize(build_init_prompt(files_content, get_repo_name(repo_path)), config)
    new_context.setdefault("project_name", get_repo_name(repo_path))
    _save(new_context, context_path, md_path)

    return f"Full scan complete. Indexed {len(new_context.get('modules', {}))} module(s)."
