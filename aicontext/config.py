import os
from pathlib import Path
from dotenv import load_dotenv


AICONTEXT_ENV_FILE = ".aicontext.env"


def load_config() -> dict:
    """Load configuration from .aicontext.env (isolated from the project's own .env)."""
    env_path = Path.cwd() / AICONTEXT_ENV_FILE
    load_dotenv(env_path, override=False)  # don't clobber already-set env vars

    return {
        "provider": os.getenv("LLM_PROVIDER", "groq").lower(),
        # Groq
        "groq_api_key": os.getenv("GROQ_API_KEY", ""),
        "groq_model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        # Ollama
        "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "ollama_model": os.getenv("OLLAMA_MODEL", "llama3"),
        # File handling
        "max_file_size_kb": int(os.getenv("MAX_FILE_SIZE_KB", "100")),
        "context_file": os.getenv("CONTEXT_FILE", "context.json"),
        "context_md_file": os.getenv("CONTEXT_MD_FILE", "context.md"),
        "ignore_dirs": set(
            os.getenv(
                "IGNORE_DIRS",
                "node_modules,.git,build,dist,__pycache__,.venv,venv,.next,.nuxt",
            ).split(",")
        ),
        "ignore_extensions": set(
            os.getenv(
                "IGNORE_EXTENSIONS",
                ".pyc,.pyo,.pyd,.so,.dylib,.dll,.exe,.bin"
                ",.jpg,.jpeg,.png,.gif,.svg,.ico,.mp4,.mp3"
                ",.zip,.tar,.gz,.lock,.sum",
            ).split(",")
        ),
    }
