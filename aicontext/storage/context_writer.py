"""Read, merge, and write context.json / context.md."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


_EMPTY: Dict[str, Any] = {
    "version": "1.0",
    "last_updated": "",
    "project_name": "",
    "summary": "",
    "modules": {},
    "recent_changes": [],
}


def load_context(path: Path) -> Dict[str, Any]:
    """Load context.json; return empty skeleton on missing/corrupt file."""
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return dict(_EMPTY)


def save_context(context: Dict[str, Any], path: Path) -> None:
    """Stamp last_updated and write context.json atomically (via temp file)."""
    context["last_updated"] = datetime.now(timezone.utc).isoformat()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(context, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)  # atomic on POSIX


def merge_context(existing: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    """Merge LLM-returned context into the existing one.

    - Top-level scalar fields (summary, project_name) are overwritten only when
      the incoming value is non-empty.
    - Module entries are upserted (existing unchanged modules are preserved).
    - recent_changes: prepend incoming entries, keep the latest 10.
    """
    merged = {**existing}

    for key in ("summary", "project_name", "version"):
        if incoming.get(key):
            merged[key] = incoming[key]

    if "modules" not in merged:
        merged["modules"] = {}
    for file_path, module_data in incoming.get("modules", {}).items():
        merged["modules"][file_path] = module_data

    new_changes = incoming.get("recent_changes", [])
    old_changes = existing.get("recent_changes", [])
    merged["recent_changes"] = (new_changes + old_changes)[:10]

    return merged


def write_markdown(context: Dict[str, Any], path: Path) -> None:
    """Render context as a human-readable Markdown file."""
    project = context.get("project_name", "Project")
    updated = context.get("last_updated", "unknown")
    summary = context.get("summary", "No summary yet.")

    lines = [
        f"# {project} — AI Context",
        f"\n> Last updated: `{updated}`",
        f"\n## Summary\n\n{summary}",
        "\n## Modules\n",
    ]

    for file_path, mod in context.get("modules", {}).items():
        lines.append(f"### `{file_path}`")
        lines.append(f"\n{mod.get('summary', '—')}\n")

        def _bullet(label: str, items):
            if items:
                lines.append(f"- **{label}:** {', '.join(str(i) for i in items)}")

        _bullet("Classes", mod.get("classes"))
        _bullet("Functions", mod.get("functions", [])[:10])  # cap long lists
        _bullet("Exports", mod.get("exports"))
        _bullet("Depends on", mod.get("dependencies"))
        lines.append("")

    lines.append("## Recent Changes\n")
    changes = context.get("recent_changes", [])
    if not changes:
        lines.append("_No changes recorded yet._\n")
    for ch in changes[:10]:
        ts = ch.get("timestamp", "")[:10]
        desc = ch.get("description", "")
        files = ", ".join(f"`{f}`" for f in ch.get("files", []))
        lines.append(f"- **{ts}** — {desc}")
        if files:
            lines.append(f"  - Files: {files}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
