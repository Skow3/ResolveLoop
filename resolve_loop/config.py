"""Configuration for the ResolveLoop MVP."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

# Load .env if present
env_file = BASE_DIR / ".env"
if env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(env_file)
    except ImportError:
        # Fallback simple parser
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

CASES_PATH = DATA_DIR / "cases.json"
MEMORY_PATH = DATA_DIR / "memories.json"
EXPERIENCES_PATH = DATA_DIR / "experiences.json"
LOG_PATH = DATA_DIR / "logs.txt"

VOICE_DIR = DATA_DIR / "voice_responses"
VOICE_DIR.mkdir(exist_ok=True)

# Agent model. Runtime uses gpt-5-nano as specified.
MODEL = os.environ.get("RESOLVELOOP_MODEL", "gpt-5-nano")
USE_LLM = os.environ.get("RESOLVELOOP_USE_LLM", "0") == "1"

# Smallest AI configuration for voice layer
SMALLEST_API_KEY = os.environ.get("SMALLEST_API_KEY", "")
SMALLEST_PULSE_URL = os.environ.get("SMALLEST_PULSE_URL", "https://waves-api.smallest.ai/api/v1/pulse/get_text")
SMALLEST_LIGHTNING_URL = os.environ.get("SMALLEST_LIGHTNING_URL", "https://api.smallest.ai/waves/v1/lightning-v3.1/get_speech")

# Timeouts (in seconds) for simulated runtime
TIMEOUT_SECONDS = int(os.environ.get("RESOLVELOOP_TIMEOUT", 60))

def ensure_data_files():
    # Create empty JSON files if they don't exist
    for p in (CASES_PATH, MEMORY_PATH, EXPERIENCES_PATH):
        if not p.exists():
            if p == CASES_PATH:
                p.write_text('{"cases": []}')
            elif p == EXPERIENCES_PATH:
                p.write_text('{"experiences": []}')
            else:
                p.write_text('{"customer_memory": {}, "case_memory": {}, "procedural_memory": {}, "failure_memory": []}')
