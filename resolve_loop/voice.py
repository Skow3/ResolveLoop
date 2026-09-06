"""Smallest AI Voice Integration Layer: Pulse STT & Lightning TTS.

Pipeline:
Customer audio -> Smallest AI Pulse STT -> ResolveLoop (gpt-5-nano) -> Resolution -> Smallest AI Lightning TTS -> Audio response.
Graceful fallback: Non-fatal error reporting if Smallest AI is unavailable; never crashes ResolveLoop.
"""
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, Union
import requests

from .config import (
    SMALLEST_API_KEY,
    SMALLEST_PULSE_URL,
    SMALLEST_LIGHTNING_URL,
    VOICE_DIR,
)
from .case import Case
from .engine import ResolveLoopEngine

class SmallestAIVoiceClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        pulse_url: Optional[str] = None,
        lightning_url: Optional[str] = None,
    ):
        self.api_key = api_key or os.environ.get("SMALLEST_API_KEY") or SMALLEST_API_KEY
        self.pulse_url = pulse_url or SMALLEST_PULSE_URL
        self.lightning_url = lightning_url or SMALLEST_LIGHTNING_URL
        VOICE_DIR.mkdir(parents=True, exist_ok=True)

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip() and not self.api_key.startswith("YOUR_"))

    def transcribe_audio_pulse(
        self,
        audio_input: Union[str, Path, bytes],
        model: str = "pulse",
    ) -> Dict[str, Any]:
        """Transcribe speech to text using Smallest AI Pulse STT.
        
        Endpoint: POST https://waves-api.smallest.ai/api/v1/pulse/get_text
        Content-Type: application/octet-stream
        """
        if not self.is_configured():
            # Graceful non-fatal fallback
            # Check if whisper is locally installed for offline fallback testing
            fallback_text = None
            try:
                if isinstance(audio_input, (str, Path)) and Path(audio_input).exists():
                    import whisper
                    wmodel = whisper.load_model("base")
                    wres = wmodel.transcribe(str(audio_input))
                    fallback_text = wres.get("text", "").strip()
            except Exception:
                pass

            return {
                "success": bool(fallback_text),
                "text": fallback_text,
                "provider": "local_whisper_fallback" if fallback_text else "none",
                "error": "SMALLEST_API_KEY is not configured in environment or .env file.",
                "note": "Voice layer operated in fallback mode. ResolveLoop text processing is unaffected."
            }

        # Read audio bytes
        try:
            if isinstance(audio_input, (str, Path)):
                audio_path = Path(audio_input)
                if not audio_path.exists():
                    return {"success": False, "text": None, "error": f"Audio file not found: {audio_path}"}
                audio_bytes = audio_path.read_bytes()
            else:
                audio_bytes = audio_input
        except Exception as e:
            return {"success": False, "text": None, "error": f"Failed to read audio input: {e}"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/octet-stream",
        }

        try:
            response = requests.post(
                self.pulse_url,
                headers=headers,
                data=audio_bytes,
                params={"model": model},
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                text = data.get("text") or data.get("transcript") or data.get("data", {}).get("text", "")
                return {
                    "success": True,
                    "text": text.strip(),
                    "provider": "smallest_ai_pulse",
                    "raw_response": data,
                    "error": None,
                }
            else:
                return {
                    "success": False,
                    "text": None,
                    "provider": "smallest_ai_pulse",
                    "error": f"Smallest AI Pulse API error ({response.status_code}): {response.text}",
                    "note": "Voice fallback triggered. Core ResolveLoop processing continues.",
                }
        except Exception as e:
            return {
                "success": False,
                "text": None,
                "provider": "smallest_ai_pulse",
                "error": f"Smallest AI Pulse connection error: {e}",
                "note": "Voice fallback triggered. Core ResolveLoop processing continues.",
            }

    def synthesize_speech_lightning(
        self,
        text: str,
        output_filename: Optional[str] = None,
        voice_id: str = "sophia",
        sample_rate: int = 24000,
    ) -> Dict[str, Any]:
        """Synthesize text to speech using Smallest AI Lightning TTS.
        
        Endpoint: POST https://api.smallest.ai/waves/v1/lightning-v3.1/get_speech
        Content-Type: application/json
        """
        timestamp = int(time.time())
        filename = output_filename or f"response_{timestamp}.wav"
        output_path = VOICE_DIR / filename

        if not self.is_configured():
            return {
                "success": False,
                "audio_path": None,
                "provider": "none",
                "error": "SMALLEST_API_KEY is not configured in environment or .env file.",
                "note": "Voice output skipped. Text resolution delivered successfully.",
            }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "text": text,
            "voice_id": voice_id,
            "sample_rate": sample_rate,
            "output_format": "wav",
        }

        try:
            response = requests.post(
                self.lightning_url,
                headers=headers,
                json=payload,
                timeout=30,
            )

            if response.status_code == 200:
                output_path.write_bytes(response.content)
                return {
                    "success": True,
                    "audio_path": str(output_path),
                    "provider": "smallest_ai_lightning",
                    "bytes_written": len(response.content),
                    "error": None,
                }
            else:
                return {
                    "success": False,
                    "audio_path": None,
                    "provider": "smallest_ai_lightning",
                    "error": f"Smallest AI Lightning TTS error ({response.status_code}): {response.text}",
                    "note": "Voice output skipped. Text resolution delivered successfully.",
                }
        except Exception as e:
            return {
                "success": False,
                "audio_path": None,
                "provider": "smallest_ai_lightning",
                "error": f"Smallest AI Lightning TTS connection error: {e}",
                "note": "Voice output skipped. Text resolution delivered successfully.",
            }

def process_voice_case(
    audio_path: Union[str, Path],
    customer_id: str = "cust1",
    engine: Optional[ResolveLoopEngine] = None,
    client: Optional[SmallestAIVoiceClient] = None,
) -> Dict[str, Any]:
    """Execute complete end-to-end voice support loop.
    
    Audio Input -> Pulse STT -> ResolveLoop Engine -> Resolution -> Lightning TTS -> Output Audio.
    """
    voice_client = client or SmallestAIVoiceClient()
    resolve_engine = engine or ResolveLoopEngine()
    
    # 1. Transcribe with Smallest AI Pulse STT
    stt_result = voice_client.transcribe_audio_pulse(audio_path)
    
    if not stt_result.get("text"):
        # If transcription completely unavailable (no key and no fallback), report non-fatal error
        return {
            "voice_enabled": False,
            "stt_result": stt_result,
            "case": None,
            "engine_result": None,
            "tts_result": None,
            "error": "Voice transcription was unable to process audio. Ensure SMALLEST_API_KEY is set.",
            "fallback_active": True,
        }

    transcribed_text = stt_result["text"]
    
    # 2. Build Case from transcribed voice input
    timestamp = int(time.time())
    case = Case(
        id=f"VOICE-{timestamp}",
        customer_id=customer_id,
        description=transcribed_text,
        priority="medium",
        metadata={"channel": "voice", "audio_source": str(audio_path), "stt_provider": stt_result.get("provider")},
    )

    # 3. Route, Solve, and Learn via ResolveLoop Engine
    engine_result = resolve_engine.run_once(case)
    response_text = engine_result.get("solve", {}).get("resolution", {}).get("response_text", "")

    # 4. Synthesize voice response with Smallest AI Lightning TTS
    tts_result = voice_client.synthesize_speech_lightning(
        text=response_text,
        output_filename=f"voice_response_{case.id}.wav",
    )

    return {
        "voice_enabled": True,
        "stt_result": stt_result,
        "case": case.to_dict(),
        "engine_result": engine_result,
        "response_text": response_text,
        "tts_result": tts_result,
        "fallback_active": not stt_result.get("success") or not tts_result.get("success"),
    }
