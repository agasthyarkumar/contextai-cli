#!/usr/bin/env python3
"""Standalone runner — safe to call from git hooks or CI without the CLI wrapper.

Usage:
    python scripts/update_context.py          # incremental diff
    python scripts/update_context.py --scan   # full project scan
"""

import sys
from pathlib import Path

# Allow running from the repo root or the scripts/ directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aicontext.orchestrator import run_update, run_full_scan  # noqa: E402


def main() -> None:
    full_scan = "--scan" in sys.argv
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    try:
        if full_scan:
            msg = run_full_scan(verbose=verbose)
        else:
            msg = run_update(verbose=verbose)
        print(f"✓ {msg}")
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
