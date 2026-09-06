"""ResolveLoop Web Application: Serving Landing Page, Voice Demo Station, and Support CRM."""
import os
import time
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

from flask import Flask, render_template, request, jsonify, send_file, send_from_directory

from .config import (
    BASE_DIR,
    DATA_DIR,
    VOICE_DIR,
    MODEL,
    USE_LLM,
    SMALLEST_API_KEY,
    ensure_data_files,
)
from .case import Case
from .engine import ResolveLoopEngine, run_comparative_benchmark
from .voice import SmallestAIVoiceClient, process_voice_case
from .mock_services import _PROFILES, _HISTORIES, _ORDERS, _PAYMENTS, _KB
from .store import ExperienceStore
from .memory import MemoryStore

# Initialize Flask
template_dir = Path(__file__).parent / "templates"
static_dir = Path(__file__).parent / "static"
template_dir.mkdir(parents=True, exist_ok=True)
static_dir.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, template_folder=str(template_dir), static_folder=str(static_dir))
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB max upload

# Shared runtime instances
engine = ResolveLoopEngine()
voice_client = SmallestAIVoiceClient()

ensure_data_files()

def normalize_audio_to_wav(input_path: Path) -> Path:
    """Ensure audio file is formatted as standard 24kHz mono PCM WAV using ffmpeg."""
    output_path = input_path.with_suffix(".norm.wav")
    try:
        cmd = [
            "ffmpeg", "-y", "-i", str(input_path),
            "-ar", "24000", "-ac", "1",
            str(output_path)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_path
    except Exception:
        # If ffmpeg conversion fails, return original path
        return input_path

# ==================== PAGE ROUTES ====================

@app.route("/")
@app.route("/landing")
def landing_page():
    return render_template("index.html", initial_view="landing", model=MODEL, use_llm=USE_LLM)

@app.route("/demo")
def demo_page():
    return render_template("index.html", initial_view="demo", model=MODEL, use_llm=USE_LLM)

@app.route("/crm")
def crm_page():
    return render_template("index.html", initial_view="crm", model=MODEL, use_llm=USE_LLM)

# ==================== API ENDPOINTS ====================

@app.route("/api/status", methods=["GET"])
def api_status():
    """Return live system configuration and operational health."""
    exp_store = ExperienceStore()
    mem_store = MemoryStore()
    return jsonify({
        "status": "online",
        "runtime_model": MODEL,
        "use_llm": USE_LLM,
        "voice_configured": voice_client.is_configured(),
        "voice_provider": "Smallest AI Pulse & Lightning" if voice_client.is_configured() else "Local Fallback Mode",
        "total_experiences": len(exp_store.get_experiences()),
        "procedural_rules_count": len(mem_store.procedural_memory),
        "active_cases": len(engine.load_cases()),
    })

@app.route("/api/voice/call", methods=["POST"])
def api_voice_call():
    """Handle incoming voice audio from the Demo call station."""
    customer_id = request.form.get("customer_id", "cust1")
    
    if "audio" not in request.files:
        return jsonify({"success": False, "error": "No audio file provided in request."}), 400

    audio_file = request.files["audio"]
    if audio_file.filename == "":
        return jsonify({"success": False, "error": "Empty filename provided."}), 400

    suffix = Path(audio_file.filename).suffix or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_in:
        temp_in_path = Path(temp_in.name)
        audio_file.save(str(temp_in_path))

    try:
        # Normalize audio via ffmpeg for 100% Smallest AI Pulse compatibility
        wav_path = normalize_audio_to_wav(temp_in_path)

        # Run complete voice pipeline
        result = process_voice_case(
            audio_path=wav_path,
            customer_id=customer_id,
            engine=engine,
            client=voice_client,
        )

        # Prepare audio URL if TTS was generated
        audio_url = None
        tts = result.get("tts_result") or {}
        if tts.get("success") and tts.get("audio_path"):
            audio_filename = Path(tts["audio_path"]).name
            audio_url = f"/api/audio/{audio_filename}"

        return jsonify({
            "success": True,
            "transcription": result.get("stt_result", {}).get("text", ""),
            "stt_provider": result.get("stt_result", {}).get("provider", "none"),
            "case": result.get("case"),
            "route": result.get("engine_result", {}).get("route"),
            "solve": result.get("engine_result", {}).get("solve"),
            "score": result.get("engine_result", {}).get("score"),
            "reflection": result.get("engine_result", {}).get("reflection"),
            "response_text": result.get("response_text"),
            "audio_url": audio_url,
            "fallback_active": result.get("fallback_active", False),
            "voice_status": "Smallest AI Pulse + Lightning Active" if not result.get("fallback_active") else "Fallback Notice",
        })
    finally:
        # Clean up temporary upload files
        try:
            if temp_in_path.exists():
                temp_in_path.unlink()
            norm_wav = temp_in_path.with_suffix(".norm.wav")
            if norm_wav.exists():
                norm_wav.unlink()
        except Exception:
            pass

@app.route("/api/text/call", methods=["POST"])
def api_text_call():
    """Handle text input from Demo call station (text fallback)."""
    data = request.get_json() or {}
    message = data.get("message", "").strip()
    customer_id = data.get("customer_id", "cust1")

    if not message:
        return jsonify({"success": False, "error": "Message text cannot be empty."}), 400

    timestamp = int(time.time())
    case = Case(
        id=f"CALL-{timestamp}",
        customer_id=customer_id,
        description=message,
        priority="medium",
        metadata={"channel": "text_fallback"},
    )

    engine_res = engine.run_once(case)
    response_text = engine_res.get("solve", {}).get("resolution", {}).get("response_text", "")

    # Synthesize speech via Smallest AI Lightning TTS if configured
    audio_url = None
    tts_result = voice_client.synthesize_speech_lightning(
        text=response_text,
        output_filename=f"voice_response_{case.id}.wav",
    )
    if tts_result.get("success") and tts_result.get("audio_path"):
        audio_filename = Path(tts_result["audio_path"]).name
        audio_url = f"/api/audio/{audio_filename}"

    return jsonify({
        "success": True,
        "transcription": message,
        "case": case.to_dict(),
        "route": engine_res.get("route"),
        "solve": engine_res.get("solve"),
        "score": engine_res.get("score"),
        "reflection": engine_res.get("reflection"),
        "response_text": response_text,
        "audio_url": audio_url,
        "tts_result": tts_result,
        "fallback_active": not tts_result.get("success"),
    })

@app.route("/api/audio/<filename>", methods=["GET"])
def api_serve_audio(filename: str):
    """Stream generated speech audio files."""
    audio_path = VOICE_DIR / filename
    if not audio_path.exists():
        # Fallback check for test.wav
        if filename == "test.wav" and (BASE_DIR / "test.wav").exists():
            return send_file(str(BASE_DIR / "test.wav"), mimetype="audio/wav")
        return jsonify({"error": "Audio file not found."}), 404
    return send_file(str(audio_path), mimetype="audio/wav")

@app.route("/api/crm/data", methods=["GET"])
def api_crm_data():
    """Return consolidated customer, order, ticket, and learning memory data."""
    exp_store = ExperienceStore()
    mem_store = MemoryStore()

    customers = []
    for cid, prof in _PROFILES.items():
        hist = _HISTORIES.get(cid, {})
        customers.append({
            "id": cid,
            "name": prof.get("name"),
            "segment": prof.get("segment"),
            "email": prof.get("email"),
            "lifetime_value": hist.get("lifetime_value", 0),
            "tickets": hist.get("tickets", []),
            "past_issues": hist.get("issues", []),
        })

    return jsonify({
        "customers": customers,
        "orders": _ORDERS,
        "payments": _PAYMENTS,
        "kb": _KB,
        "experiences": exp_store.get_experiences(),
        "procedural_memory": mem_store.procedural_memory,
        "failure_memory": mem_store.failure_memory,
        "case_memory": mem_store.case_memory,
    })

@app.route("/api/benchmark/run", methods=["POST"])
def api_run_benchmark():
    """Trigger the two-pass before/after learning benchmark."""
    res = run_comparative_benchmark()
    return jsonify(res)

def start_server(host="0.0.0.0", port=5000, debug=False):
    print(f"Starting ResolveLoop Web Server on http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)

if __name__ == "__main__":
    start_server(port=int(os.environ.get("PORT", 5000)))
