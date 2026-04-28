"""LLM provider abstraction.

Supported backends:
  - groq   → Groq Cloud (default)
  - ollama → local Ollama instance (OpenAI-compatible /v1 endpoint)

Adding a new provider: implement call_<name>(prompt, config) -> str
and register it in PROVIDERS below.
"""

import json as _json
from typing import Any, Dict


# ── Groq ──────────────────────────────────────────────────────────────────────

def call_groq(prompt: str, config: dict) -> str:
    try:
        from groq import Groq, AuthenticationError, RateLimitError, APIStatusError
    except ImportError:
        raise RuntimeError("groq package missing — run: pip install groq")

    api_key = config.get("groq_api_key", "")
    if not api_key or api_key == "your_groq_api_key_here":
        raise RuntimeError(
            "GROQ_API_KEY is not set.\n"
            "  1. Open .aicontext.env\n"
            "  2. Replace 'your_groq_api_key_here' with your real key from console.groq.com"
        )

    try:
        response = Groq(api_key=api_key).chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=config.get("groq_model", "llama-3.3-70b-versatile"),
            temperature=0.1,
            max_tokens=4096,
        )
    except AuthenticationError:
        raise RuntimeError(
            "Invalid Groq API key (401).\n"
            "  1. Open .aicontext.env\n"
            "  2. Set GROQ_API_KEY to a valid key from console.groq.com"
        )
    except RateLimitError:
        raise RuntimeError(
            "Groq rate limit reached. Wait a moment and try again, "
            "or switch to a different model in .aicontext.env"
        )
    except APIStatusError as exc:
        raise RuntimeError(f"Groq API error {exc.status_code}: {exc.message}") from exc

    return response.choices[0].message.content


# ── Ollama ─────────────────────────────────────────────────────────────────────

def call_ollama(prompt: str, config: dict) -> str:
    """Call a local Ollama instance via its OpenAI-compatible /v1 endpoint."""
    import urllib.request

    base_url = config.get("ollama_base_url", "http://localhost:11434").rstrip("/")
    payload = _json.dumps({
        "model": config.get("ollama_model", "llama3"),
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "temperature": 0.1,
    }).encode()

    req = urllib.request.Request(
        f"{base_url}/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return _json.loads(resp.read())["choices"][0]["message"]["content"]
    except Exception as exc:
        raise RuntimeError(f"Ollama request failed: {exc}") from exc


# ── Registry ───────────────────────────────────────────────────────────────────

PROVIDERS = {
    "groq": call_groq,
    "ollama": call_ollama,
}


# ── Public API ─────────────────────────────────────────────────────────────────

def summarize(prompt: str, config: dict) -> Dict[str, Any]:
    """Call the configured LLM and return a parsed JSON context dict."""
    provider = config.get("provider", "groq")
    caller = PROVIDERS.get(provider)
    if caller is None:
        raise RuntimeError(
            f"Unknown LLM provider '{provider}'. Supported: {', '.join(PROVIDERS)}"
        )
    return _parse_json(caller(prompt, config))


def _parse_json(raw: str) -> Dict[str, Any]:
    """Extract JSON from an LLM response, stripping markdown fences if present."""
    text = raw.strip()

    # Strip ```json ... ``` or ``` ... ``` wrappers
    if "```" in text:
        for part in text.split("```")[1::2]:   # odd indices = inside fences
            try:
                return _json.loads(part.lstrip("json").strip())
            except _json.JSONDecodeError:
                continue

    # Try the whole response
    try:
        return _json.loads(text)
    except _json.JSONDecodeError:
        pass

    # Last resort: find the outermost { … }
    start, end = text.find("{"), text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return _json.loads(text[start:end])
        except _json.JSONDecodeError:
            pass

    raise RuntimeError(
        f"Could not parse JSON from LLM response.\nFirst 400 chars: {raw[:400]}"
    )
