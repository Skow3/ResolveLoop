"""OpenAI API wrapper for ResolveLoop runtime agents (model: gpt-5-nano)."""
import os
import json
from typing import Optional, Dict, Any, List

MODEL = os.environ.get("RESOLVELOOP_MODEL", "gpt-5-nano")

def request_llm(prompt: str, model: str = MODEL, system_prompt: Optional[str] = None) -> Optional[str]:
    """Execute an LLM chat completion using OpenAI API.
    
    Returns string response if enabled and successful, else None.
    """
    use_llm = os.environ.get("RESOLVELOOP_USE_LLM", "0")
    if use_llm != "1":
        return None

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    # Strategy 1: Attempt official OpenAI client if available
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
        )
        return response.choices[0].message.content
    except ImportError:
        pass
    except Exception as e:
        # If model name gpt-5-nano is rejected or network error occurs, fail gracefully
        pass

    # Strategy 2: Direct REST call via requests
    try:
        import requests
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
        }
        res = requests.post(url, headers=headers, json=payload, timeout=20)
        if res.status_code == 200:
            data = res.json()
            return data["choices"][0]["message"]["content"]
    except Exception:
        pass

    return None
