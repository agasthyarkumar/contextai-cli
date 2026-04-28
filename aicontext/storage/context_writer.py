"""Read, merge, and write context.json / context.md."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


_EMPTY: Dict[str, Any] = {
    "version": "1.0",
    "last_updated": "",
    "project_name": "",
    "summary": "",
    "modules": {},
    "recent_changes": [],
}


def load_context(path: Path) -> Dict[str, Any]:
    """Load context.json; return empty skeleton on missing or corrupt file."""
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return dict(_EMPTY)


def save_context(context: Dict[str, Any], path: Path) -> None:
    """Stamp last_updated and write context.json atomically via a temp file."""
    context["last_updated"] = datetime.now(timezone.utc).isoformat()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(context, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)   # atomic on POSIX


def merge_context(existing: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    """Merge LLM-returned context into existing, preserving unchanged modules."""
    merged = {**existing}

    for key in ("summary", "project_name", "version"):
        if incoming.get(key):
            merged[key] = incoming[key]

    merged.setdefault("modules", {}).update(incoming.get("modules", {}))

    merged["recent_changes"] = (
        incoming.get("recent_changes", []) + existing.get("recent_changes", [])
    )[:10]

    return merged


# ── Markdown helpers ───────────────────────────────────────────────────────────

def _bullet(label: str, items: List) -> str:
    if items:
        return f"- **{label}:** {', '.join(str(i) for i in items)}"
    return ""


def write_markdown(context: Dict[str, Any], path: Path) -> None:
    """Render context as a human-readable Markdown file."""
    lines = [
        f"# {context.get('project_name', 'Project')} — AI Context",
        f"\n> Last updated: `{context.get('last_updated', 'unknown')}`",
        f"\n## Summary\n\n{context.get('summary', 'No summary yet.')}",
        "\n## Modules\n",
    ]

    for file_path, mod in context.get("modules", {}).items():
        lines.append(f"### `{file_path}`")
        lines.append(f"\n{mod.get('summary', '—')}\n")
        for line in (
            _bullet("Classes", mod.get("classes")),
            _bullet("Functions", mod.get("functions", [])[:10]),
            _bullet("Exports", mod.get("exports")),
            _bullet("Depends on", mod.get("dependencies")),
        ):
            if line:
                lines.append(line)
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
