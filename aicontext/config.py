import os
from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv

AICONTEXT_ENV_FILE = ".aicontext.env"


@lru_cache(maxsize=1)
def load_config() -> dict:
    """Load configuration from .aicontext.env once and cache for the process lifetime."""
    env_path = Path.cwd() / AICONTEXT_ENV_FILE
    load_dotenv(env_path, override=False)  # never clobber already-set env vars

    try:
        max_file_size_kb = int(os.getenv("MAX_FILE_SIZE_KB", "100"))
    except ValueError:
        max_file_size_kb = 100

    return {
        "provider": os.getenv("LLM_PROVIDER", "groq").lower(),
        "groq_api_key": os.getenv("GROQ_API_KEY", ""),
        "groq_model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "ollama_model": os.getenv("OLLAMA_MODEL", "llama3"),
        "max_file_size_kb": max_file_size_kb,
        "context_file": os.getenv("CONTEXT_FILE", "context.json"),
        "context_md_file": os.getenv("CONTEXT_MD_FILE", "context.md"),
        "ignore_dirs": frozenset(
            os.getenv(
                "IGNORE_DIRS",
                "node_modules,.git,build,dist,__pycache__,.venv,venv,.next,.nuxt",
            ).split(",")
        ),
        "ignore_extensions": frozenset(
            os.getenv(
                "IGNORE_EXTENSIONS",
                ".pyc,.pyo,.pyd,.so,.dylib,.dll,.exe,.bin"
                ",.jpg,.jpeg,.png,.gif,.svg,.ico,.mp4,.mp3"
                ",.zip,.tar,.gz,.lock,.sum",
            ).split(",")
        ),
    }
