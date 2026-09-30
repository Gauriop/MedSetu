"""LLM backend switch.
LLM_BACKEND=groq    -> existing Groq client from summarize.get_client (default)
LLM_BACKEND=ollama  -> local Llama 3.1 8B through Ollama (ollama pull llama3.1:8b)"""
import os

import config  # noqa: F401


def generate(system: str, user: str, temperature: float = 0.1) -> str:
    backend = os.getenv("LLM_BACKEND", "groq").lower()
    if backend == "ollama":
        import requests
        r = requests.post(
            os.getenv("OLLAMA_URL", "http://localhost:11434") + "/api/chat",
            json={
                "model": os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "stream": False,
                "options": {"temperature": temperature},
            },
            timeout=600,
        )
        r.raise_for_status()
        return r.json()["message"]["content"].strip()

    from summarize import get_client
    resp = get_client().chat.completions.create(
        model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
    )
    return resp.choices[0].message.content.strip()