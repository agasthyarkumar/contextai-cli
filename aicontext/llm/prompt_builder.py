import json
from typing import Dict, Any


def build_update_prompt(
    existing_context: Dict[str, Any],
    changed_files: Dict[str, str],
    diff_summary: str = "",
) -> str:
    """Build a prompt for incremental context update (diff-mode)."""

    # Keep existing context concise to save tokens
    existing_json = json.dumps(existing_context, indent=2)[:3000]

    files_section = ""
    for path, content in changed_files.items():
        files_section += f"\n### {path}\n```\n{content[:1500]}\n```\n"

    diff_block = diff_summary[:1500] if diff_summary else "Not available"

    return f"""\
You are a senior engineer maintaining a compressed, structured JSON context of a codebase.

## Existing context (JSON):
{existing_json}

## Files that changed:
{files_section}

## Git diff (excerpt):
```diff
{diff_block}
```

## Task:
1. For every changed file, update its entry inside "modules" with a fresh 1-sentence summary, key function/class names, and direct imports of other project files.
2. Remove a module entry only if the file was deleted.
3. Append ONE entry to "recent_changes" describing this batch of changes. Keep at most 10 entries total (drop the oldest).
4. Update "summary" only if the overall architecture changed meaningfully.
5. Be concise — module summaries must be ≤ 2 sentences.

## Output rules:
- Return ONLY valid JSON. No markdown fences. No explanation text.
- Use this exact schema:

{{
  "version": "1.0",
  "last_updated": "<RFC-3339 timestamp>",
  "project_name": "<name>",
  "summary": "<1–3 sentence project overview>",
  "modules": {{
    "<relative/file/path>": {{
      "summary": "<what this file does>",
      "functions": ["<name>"],
      "classes": ["<name>"],
      "exports": ["<name>"],
      "dependencies": ["<other relative path>"]
    }}
  }},
  "recent_changes": [
    {{
      "timestamp": "<RFC-3339>",
      "files": ["<path>"],
      "description": "<concise change description>"
    }}
  ]
}}
"""


def build_init_prompt(files: Dict[str, str], project_name: str) -> str:
    """Build a prompt for a full initial scan of the project."""

    files_section = ""
    for path, content in list(files.items())[:25]:  # cap to avoid huge prompts
        files_section += f"\n### {path}\n```\n{content[:1000]}\n```\n"

    return f"""\
You are a senior engineer. Analyse this codebase and produce a structured JSON context document.

## Project: {project_name}

## Source files:
{files_section}

## Task:
1. Write a concise 1–3 sentence summary of what this project does.
2. For each file above, write a 1-sentence summary and list key functions, classes, and exports.
3. Note which project files each module imports from (skip stdlib/third-party).
4. Leave "recent_changes" as an empty array.

## Output rules:
- Return ONLY valid JSON. No markdown fences. No explanation text.

{{
  "version": "1.0",
  "last_updated": "<RFC-3339 timestamp>",
  "project_name": "{project_name}",
  "summary": "<overview>",
  "modules": {{
    "<relative/file/path>": {{
      "summary": "<what this file does>",
      "functions": ["<name>"],
      "classes": ["<name>"],
      "exports": ["<name>"],
      "dependencies": []
    }}
  }},
  "recent_changes": []
}}
"""
