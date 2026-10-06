"""LLM backend switch.

LLM_BACKEND=groq    -> Groq client from summarize.get_client (default)
LLM_BACKEND=ollama  -> local Llama 3.1 8B through Ollama (ollama pull llama3.1:8b)

Optional env vars (all have defaults):
    GROQ_MODEL     model name            (default: openai/gpt-oss-20b)
    GROQ_MAX_OUT   max output tokens     (default: 1000)
"""
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

    # ---- Groq ----
    from groq import APIStatusError
    from summarize import get_client

    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    # Groq counts the reserved output tokens toward the per-minute limit,
    # so cap the answer instead of leaving the model default.
    max_out = int(os.getenv("GROQ_MAX_OUT", "1000"))

    tail_len = 400  # the question sits at the end of the prompt, so keep it

    for attempt in range(3):
        try:
            resp = get_client().chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
                max_completion_tokens=max_out,
            )
            return resp.choices[0].message.content.strip()
        except APIStatusError as e:
            # Only retry "request too large" errors, and only twice.
            if e.status_code != 413 or attempt == 2 or len(user) <= 1500:
                raise
            half = len(user) // 2
            user = user[: half - tail_len] + "\n...\n" + user[-tail_len:]
            print(f"[llm] 413, retrying with {len(user)} chars (attempt {attempt + 2})")
