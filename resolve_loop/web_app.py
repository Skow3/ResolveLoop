"""ResolveLoop / Maximor AI Web Application.

Serves Landing Page, Hands-Free Voice Demo Station, and Finance Operations CRM.
Integrates PostgreSQL database, Smallest AI Pulse STT & Lightning TTS, and OpenAI gpt-5-nano.
"""
import os
import time
import json
import uuid
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
    DATABASE_URL,
    ensure_data_files,
)
from .case import Case
from .engine import ResolveLoopEngine, run_comparative_benchmark
from .voice import SmallestAIVoiceClient, process_voice_case
from .mock_services import _PROFILES, _HISTORIES, _ORDERS, _PAYMENTS, _KB
from .store import ExperienceStore
from .memory import MemoryStore
from .db import db
from .finance_tools import (
    get_customer,
    record_feedback,
    record_audit_event,
)

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

    pg_healthy = False
    try:
        db_check = db.fetch_one("SELECT 1 as ok;")
        pg_healthy = bool(db_check and db_check.get("ok") == 1)
    except Exception:
        pg_healthy = False

    return jsonify({
        "status": "online",
        "runtime_model": MODEL,
        "use_llm": USE_LLM,
        "voice_configured": voice_client.is_configured(),
        "voice_provider": "Smallest AI Pulse & Lightning" if voice_client.is_configured() else "Local Fallback Mode",
        "database_backend": "PostgreSQL (maximor_finance)" if pg_healthy else "SQLite / Fallback",
        "total_experiences": len(exp_store.get_experiences()),
        "procedural_rules_count": len(mem_store.procedural_memory),
        "active_cases": len(engine.load_cases()),
    })

@app.route("/api/voice/greet", methods=["POST"])
def api_voice_greet():
    """Generate dynamic greeting speech for starting a hands-free simulated customer call."""
    data = request.get_json() or {}
    customer_id = data.get("customer_id", "cust1")

    # Fetch customer profile
    cust = get_customer(customer_id)
    name = cust.get("name", "there")
    greeting_text = f"Thanks for calling Maximor AI. Hi {name}, how can I help you today?"

    audio_url = None
    tts_result = {"success": False}
    try:
        timestamp = int(time.time())
        tts_result = voice_client.synthesize_speech_lightning(
            text=greeting_text,
            output_filename=f"greet_{customer_id}_{timestamp}.wav",
        )
        if tts_result.get("success") and tts_result.get("audio_path"):
            audio_filename = Path(tts_result["audio_path"]).name
            audio_url = f"/api/audio/{audio_filename}"
    except Exception as e:
        tts_result = {"success": False, "error": str(e)}

    # Record audit event
    record_audit_event(None, "CALL_INITIALIZED_GREETING", {"customer_id": customer_id, "name": name, "voice": bool(audio_url)})

    return jsonify({
        "success": True,
        "greeting_text": greeting_text,
        "customer": cust,
        "audio_url": audio_url,
        "tts_result": tts_result,
        "fallback_active": not bool(audio_url),
    })

@app.route("/api/feedback", methods=["POST"])
def api_feedback():
    """Store thumbs up / down feedback linked to case and update learning weights."""
    data = request.get_json() or {}
    case_id = data.get("case_id")
    rating = data.get("rating", "positive")
    reason = data.get("reason")
    comment = data.get("comment")
    interaction_id = data.get("interaction_id")

    if not case_id:
        return jsonify({"success": False, "error": "Missing required field: case_id"}), 400

    try:
        result = record_feedback(
            case_id=case_id,
            rating=rating,
            reason=reason,
            comment=comment,
            interaction_id=interaction_id,
        )
        return jsonify({"success": True, **result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

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
        wav_path = normalize_audio_to_wav(temp_in_path)

        result = process_voice_case(
            audio_path=wav_path,
            customer_id=customer_id,
            engine=engine,
            client=voice_client,
        )

        audio_url = None
        tts = result.get("tts_result") or {}
        if tts.get("success") and tts.get("audio_path"):
            audio_filename = Path(tts["audio_path"]).name
            audio_url = f"/api/audio/{audio_filename}"

        eng_res = result.get("engine_result") or {}
        solve_res = eng_res.get("solve") or {}
        resolution = solve_res.get("resolution") or {}

        return jsonify({
            "success": True,
            "transcription": result.get("stt_result", {}).get("text", ""),
            "stt_provider": result.get("stt_result", {}).get("provider", "none"),
            "case": result.get("case"),
            "case_id": result.get("case", {}).get("id"),
            "route": eng_res.get("route"),
            "solve": solve_res,
            "score": eng_res.get("score"),
            "reflection": eng_res.get("reflection"),
            "response_text": result.get("response_text"),
            "evidence": resolution.get("evidence", []),
            "domain": resolution.get("domain", "general_finance"),
            "confidence": resolution.get("confidence", 0.94),
            "ticket": resolution.get("ticket", "MX-1042"),
            "audio_url": audio_url,
            "fallback_active": result.get("fallback_active", False),
            "voice_status": "Smallest AI Pulse + Lightning Active" if not result.get("fallback_active") else "Fallback Notice",
        })
    finally:
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
        id=f"MX-{timestamp}",
        customer_id=customer_id,
        description=message,
        priority="medium",
        metadata={"channel": "text_fallback", "domain": "finance_operations"},
    )

    engine_res = engine.run_once(case)
    solve_res = engine_res.get("solve", {})
    resolution = solve_res.get("resolution", {})
    response_text = resolution.get("response_text", "")

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
        "case_id": case.id,
        "route": engine_res.get("route"),
        "solve": solve_res,
        "score": engine_res.get("score"),
        "reflection": engine_res.get("reflection"),
        "response_text": response_text,
        "evidence": resolution.get("evidence", []),
        "domain": resolution.get("domain", "general_finance"),
        "confidence": resolution.get("confidence", 0.94),
        "ticket": resolution.get("ticket", f"MX-{timestamp}"),
        "audio_url": audio_url,
        "tts_result": tts_result,
        "fallback_active": not tts_result.get("success"),
    })

@app.route("/api/audio/<filename>", methods=["GET"])
def api_serve_audio(filename: str):
    """Stream generated speech audio files."""
    audio_path = VOICE_DIR / filename
    if not audio_path.exists():
        if filename == "test.wav" and (BASE_DIR / "test.wav").exists():
            return send_file(str(BASE_DIR / "test.wav"), mimetype="audio/wav")
        return jsonify({"error": "Audio file not found."}), 404
    return send_file(str(audio_path), mimetype="audio/wav")

@app.route("/api/crm/data", methods=["GET"])
def api_crm_data():
    """Return consolidated finance operations CRM data from PostgreSQL."""
    exp_store = ExperienceStore()
    mem_store = MemoryStore()

    customers = []
    organizations = []
    finance_systems = []
    finance_records = []
    policies = []
    audit_events = []
    experiences = []

    try:
        customers = db.fetch_all("SELECT * FROM customers ORDER BY name;")
        organizations = db.fetch_all("SELECT * FROM organizations ORDER BY name;")
        finance_systems = db.fetch_all("SELECT * FROM finance_systems ORDER BY name;")
        finance_records = db.fetch_all("SELECT * FROM finance_records ORDER BY transaction_date DESC LIMIT 25;")
        policies = db.fetch_all("SELECT * FROM policies ORDER BY policy_code;")
        audit_events = db.fetch_all("SELECT * FROM audit_events ORDER BY created_at DESC LIMIT 20;")
        experiences = db.fetch_all("SELECT * FROM experiences ORDER BY confidence DESC LIMIT 15;")
    except Exception:
        pass

    # Fallback to local memory stores if DB returned empty
    if not experiences:
        experiences = exp_store.get_experiences()

    if not customers:
        for cid, prof in _PROFILES.items():
            hist = _HISTORIES.get(cid, {})
            customers.append({
                "id": cid,
                "name": prof.get("name"),
                "segment": prof.get("segment"),
                "email": prof.get("email"),
                "role": "Finance Contact",
                "account_status": "good_standing",
                "lifetime_value": hist.get("lifetime_value", 0),
            })

    return jsonify({
        "customers": customers,
        "organizations": organizations,
        "finance_systems": finance_systems,
        "finance_records": finance_records,
        "policies": policies,
        "audit_events": audit_events,
        "experiences": experiences,
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
    print(f"Starting Maximor AI Web Server on http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)

if __name__ == "__main__":
    start_server(port=int(os.environ.get("PORT", 5000)))
