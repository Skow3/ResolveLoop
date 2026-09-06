"""Configuration for the ResolveLoop MVP."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

CASES_PATH = DATA_DIR / "cases.json"
MEMORY_PATH = DATA_DIR / "memories.json"
EXPERIENCES_PATH = DATA_DIR / "experiences.json"
LOG_PATH = DATA_DIR / "logs.txt"

# Agent model (mockable). In prod, this would be the OpenAI gpt-5-nano model.
MODEL = os.environ.get("RESOLVELOOP_MODEL", "gpt-5-nano")

# Timeouts (in seconds) for simulated runtime
TIMEOUT_SECONDS = int(os.environ.get("RESOLVELOOP_TIMEOUT", 60))

def ensure_data_files():
    # Create empty JSON files if they don't exist
    for p in (CASES_PATH, MEMORY_PATH, EXPERIENCES_PATH):
        if not p.exists():
            p.write_text("{}" if p.suffix == ".json" else "")
