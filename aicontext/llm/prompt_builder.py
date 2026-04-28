import json
from typing import Dict, Any

_SCHEMA = """\
{
  "version": "1.0",
  "last_updated": "<RFC-3339 timestamp>",
  "project_name": "<name>",
  "summary": "<1–3 sentence project overview>",
  "modules": {
    "<relative/file/path>": {
      "summary": "<what this file does>",
      "functions": ["<name>"],
      "classes": ["<name>"],
      "exports": ["<name>"],
      "dependencies": ["<other relative path>"]
    }
  },
  "recent_changes": [
    {
      "timestamp": "<RFC-3339>",
      "files": ["<path>"],
      "description": "<concise change description>"
    }
  ]
}"""


def _files_block(files: Dict[str, str], content_cap: int) -> str:
    parts = []
    for path, content in files.items():
        parts.append(f"\n### {path}\n```\n{content[:content_cap]}\n```")
    return "\n".join(parts)


def build_update_prompt(
    existing_context: Dict[str, Any],
    changed_files: Dict[str, str],
    diff_summary: str = "",
) -> str:
    existing_json = json.dumps(existing_context, indent=2)[:3000]
    diff_block = diff_summary[:1500] if diff_summary else "Not available"

    return (
        "You are a senior engineer maintaining a compressed, structured JSON context of a codebase.\n\n"
        "## Existing context (JSON):\n"
        f"{existing_json}\n\n"
        "## Files that changed:\n"
        f"{_files_block(changed_files, 1500)}\n\n"
        "## Git diff (excerpt):\n"
        f"```diff\n{diff_block}\n```\n\n"
        "## Task:\n"
        "1. For every changed file, update its entry inside \"modules\" with a fresh 1-sentence summary, key function/class names, and direct imports of other project files.\n"
        "2. Remove a module entry only if the file was deleted.\n"
        "3. Append ONE entry to \"recent_changes\" describing this batch of changes. Keep at most 10 entries total (drop the oldest).\n"
        "4. Update \"summary\" only if the overall architecture changed meaningfully.\n"
        "5. Be concise — module summaries must be ≤ 2 sentences.\n\n"
        "## Output rules:\n"
        "- Return ONLY valid JSON. No markdown fences. No explanation text.\n"
        f"- Use this exact schema:\n\n{_SCHEMA}\n"
    )


def build_init_prompt(files: Dict[str, str], project_name: str) -> str:
    init_schema = _SCHEMA.replace(
        '"recent_changes": [\n    {\n      "timestamp": "<RFC-3339>",\n      "files": ["<path>"],\n      "description": "<concise change description>"\n    }\n  ]',
        '"recent_changes": []'
    )

    return (
        "You are a senior engineer. Analyse this codebase and produce a structured JSON context document.\n\n"
        f"## Project: {project_name}\n\n"
        "## Source files:\n"
        f"{_files_block(dict(list(files.items())[:25]), 1000)}\n\n"
        "## Task:\n"
        "1. Write a concise 1–3 sentence summary of what this project does.\n"
        "2. For each file above, write a 1-sentence summary and list key functions, classes, and exports.\n"
        "3. Note which project files each module imports from (skip stdlib/third-party).\n"
        "4. Leave \"recent_changes\" as an empty array.\n\n"
        "## Output rules:\n"
        "- Return ONLY valid JSON. No markdown fences. No explanation text.\n\n"
        f"{init_schema}\n"
    )
