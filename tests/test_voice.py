import unittest
from pathlib import Path
from resolve_loop.voice import SmallestAIVoiceClient, process_voice_case
from resolve_loop.config import BASE_DIR

class TestVoiceLayer(unittest.TestCase):
    def test_voice_client_unconfigured_fallback(self):
        """Verify Smallest AI client behaves gracefully when API key is unset."""
        client = SmallestAIVoiceClient(api_key="")
        self.assertFalse(client.is_configured())

        # Lightning TTS fallback
        tts_res = client.synthesize_speech_lightning("Hello world")
        self.assertFalse(tts_res["success"])
        self.assertIn("not configured", tts_res["error"])

        # Pulse STT non-fatal fallback
        stt_res = client.transcribe_audio_pulse(b"fake_audio_bytes")
        self.assertIn("not configured", stt_res.get("error", ""))

    def test_process_voice_case_with_wav(self):
        """Verify end-to-end voice case processing handles real wav file."""
        wav_path = BASE_DIR / "test.wav"
        if not wav_path.exists():
            self.skipTest("test.wav not present")

        result = process_voice_case(wav_path)
        self.assertTrue(result.get("voice_enabled") or result.get("fallback_active"))
        if result.get("case"):
            self.assertIn("Hello", result["case"]["description"])
            self.assertIsNotNone(result.get("response_text"))

if __name__ == "__main__":
    unittest.main()
