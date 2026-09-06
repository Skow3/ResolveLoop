"""Lightweight wrapper to call OpenAI GPT-5-nano if configured."""
import os
from typing import Optional

MODEL = "gpt-5-nano"

def request_llm(prompt: str, model: str = MODEL) -> Optional[str]:
    use_llm = os.environ.get("RESOLVELOOP_USE_LLM", "0")
    if use_llm != "1":
        return None
    try:
        import openai
        # If OpenAI API key is not configured, this will error gracefully.
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            openai.api_key = api_key
        # Build a minimal chat session
        response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.get("content", "")
    except Exception:
        return None
