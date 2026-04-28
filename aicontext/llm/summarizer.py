"""LLM provider abstraction.

Supported backends:
  - groq    → Groq Cloud (default)
  - ollama  → local Ollama instance (OpenAI-compatible /v1 endpoint)

Adding a new provider: implement a call_<name>(prompt, config) -> str function
and register it in the PROVIDERS dict at the bottom.
"""

import json as _json
from typing import Dict, Any


# ── Groq ──────────────────────────────────────────────────────────────────────

def call_groq(prompt: str, config: dict) -> str:
    try:
        from groq import Groq
    except ImportError:
        raise RuntimeError("groq package missing — run: pip install groq")

    api_key = config.get("groq_api_key", "")
    if not api_key or api_key == "your_groq_api_key_here":
        raise RuntimeError(
            "GROQ_API_KEY is not set.\n"
            "  1. Open .aicontext.env\n"
            "  2. Replace 'your_groq_api_key_here' with your real key from console.groq.com"
        )

    from groq import AuthenticationError, RateLimitError, APIStatusError

    client = Groq(api_key=api_key)
    try:
        response = client.chat.completions.create(
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
            data = _json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
    except Exception as exc:
        raise RuntimeError(f"Ollama request failed: {exc}") from exc


# ── Registry ───────────────────────────────────────────────────────────────────

PROVIDERS = {
    "groq": call_groq,
    "ollama": call_ollama,
}


# ── Public API ─────────────────────────────────────────────────────────────────

def summarize(prompt: str, config: dict) -> Dict[str, Any]:
    """Call the configured LLM and return parsed JSON context dict."""
    provider = config.get("provider", "groq")
    caller = PROVIDERS.get(provider)
    if caller is None:
        supported = ", ".join(PROVIDERS)
        raise RuntimeError(
            f"Unknown LLM provider '{provider}'. Supported: {supported}"
        )

    raw = caller(prompt, config)
    return _parse_json(raw)


def _parse_json(raw: str) -> Dict[str, Any]:
    """Extract JSON from the LLM response, stripping markdown fences if needed."""
    text = raw.strip()

    # Strip ```json ... ``` or ``` ... ``` wrappers
    if "```" in text:
        parts = text.split("```")
        # parts[1] is inside the first fence pair
        for part in parts[1::2]:  # odd indices are inside fences
            candidate = part.lstrip("json").strip()
            try:
                return _json.loads(candidate)
            except _json.JSONDecodeError:
                continue

    # Try to parse the whole response as JSON
    try:
        return _json.loads(text)
    except _json.JSONDecodeError:
        pass

    # Last resort: find the outermost { … }
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return _json.loads(text[start:end])
        except _json.JSONDecodeError:
            pass

    raise RuntimeError(
        f"Could not parse JSON from LLM response.\n"
        f"First 400 chars: {raw[:400]}"
    )
