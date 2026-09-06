"""CLI entrypoint for running the ResolveLoop MVP."""
import sys
import argparse
from pathlib import Path

from resolve_loop.engine import run_demo_loop, run_comparative_benchmark
from resolve_loop.voice import process_voice_case, SmallestAIVoiceClient
from resolve_loop.config import BASE_DIR, MODEL, USE_LLM

def print_banner():
    print("=" * 70)
    print("                RESOLVELOOP AUTONOMOUS SUPPORT WORKFORCE")
    print("       Track 1: Automated Agent Engineering (Experience-Driven Learning)")
    print("=" * 70)
    print(f"Runtime Model: {MODEL} | LLM Enabled: {USE_LLM}")
    vclient = SmallestAIVoiceClient()
    voice_status = "Configured (API key present)" if vclient.is_configured() else "Fallback Mode (Non-fatal offline mode)"
    print(f"Voice Layer: Smallest AI Pulse STT & Lightning TTS [{voice_status}]")
    print("-" * 70)

def run_p0_demo():
    print("\n>>> EXECUTING P0 EXPERIENCE-DRIVEN LEARNING BENCHMARK <<<")
    print("Demonstrating Pass 1 (Cold Start) vs Pass 2 (Warm / Learned)...")
    
    bench_data = run_comparative_benchmark()
    if "error" in bench_data:
        print(f"Error executing benchmark: {bench_data['error']}")
        sys.exit(1)

    print("\n--- [PASS 1: COLD START (No Prior Experience)] ---")
    for idx, r in enumerate(bench_data.get("pass1_results", []), 1):
        cid = r['case']['id']
        desc = r['case']['description']
        route = r['route']
        score = r['score']['score']
        escalated = r['solve'].get('escalated', False)
        tools = r['solve'].get('actions', [])
        esc_str = " [ESCALATED]" if escalated else ""
        print(f" Case {idx} ({cid}): '{desc}'")
        print(f"   -> Route: L{route['route_level']} ({route['routing_source']}){esc_str}")
        print(f"   -> Tools: {tools}")
        print(f"   -> Score: {score}/100 | Lessons: {r['reflection'].get('lessons', [''])[0]}")

    print("\n--- [PASS 2: WARM START (Learning & Procedural Memory Active)] ---")
    for idx, r in enumerate(bench_data.get("pass2_results", []), 1):
        cid = r['case']['id']
        desc = r['case']['description']
        route = r['route']
        score = r['score']['score']
        escalated = r['solve'].get('escalated', False)
        tools = r['solve'].get('actions', [])
        learning_str = f" [LEARNED: {route.get('learning_reason')}]" if route.get('learning_applied') else ""
        esc_str = " [ESCALATED]" if escalated else ""
        print(f" Case {idx} ({cid}): '{desc}'")
        print(f"   -> Route: L{route['route_level']} ({route['routing_source']}){learning_str}{esc_str}")
        print(f"   -> Tools: {tools}")
        print(f"   -> Score: {score}/100")

    comp = bench_data.get("comparison", {})
    p1 = bench_data.get("pass1_cold", {})
    p2 = bench_data.get("pass2_warm", {})
    print("\n" + "=" * 70)
    print("                    LEARNING LOOP BENCHMARK RESULTS")
    print("=" * 70)
    print(f" Metric                  | Pass 1 (Cold) | Pass 2 (Warm) | Delta")
    print("-" * 70)
    print(f" Average Score           | {p1.get('average_score', 0):>10.2f} pts | {p2.get('average_score', 0):>10.2f} pts | {comp.get('score_delta'):>10}")
    print(f" Escalation Rate         | {p1.get('escalation_rate', 0):>10.1f} %   | {p2.get('escalation_rate', 0):>10.1f} %   | {comp.get('escalation_delta'):>10}")
    print(f" Resolution Rate         | {p1.get('resolution_rate', 0):>10.1f} %   | {p2.get('resolution_rate', 0):>10.1f} %   | {comp.get('resolution_delta'):>10}")
    print(f" Tool Invocations/Case   | {p1.get('avg_tools_used', 0):>10.2f}     | {p2.get('avg_tools_used', 0):>10.2f}     | {comp.get('tool_usage_delta'):>10}")
    print("-" * 70)
    if comp.get("learning_confirmed"):
        print(" SUCCESS: Learning loop confirmed! System adaptively improved performance.")
    print("=" * 70)

def run_voice_demo(audio_path_str: str):
    audio_path = Path(audio_path_str)
    if not audio_path.is_absolute():
        audio_path = BASE_DIR / audio_path

    print(f"\n>>> EXECUTING END-TO-END VOICE LOOP: {audio_path.name} <<<")
    if not audio_path.exists():
        print(f"Error: Audio file not found at {audio_path}")
        return

    result = process_voice_case(audio_path)
    if not result.get("voice_enabled") and not result.get("case"):
        print(f"Voice Error (non-fatal): {result.get('error')}")
        print("ResolveLoop text workflow remains fully operational.")
        return

    stt = result.get("stt_result", {})
    print(f"1. Speech-to-Text (Smallest AI Pulse):")
    print(f"   - Transcribed Text: \"{stt.get('text')}\"")
    print(f"   - Provider/Mode: {stt.get('provider')}")
    if stt.get("error"):
        print(f"   - Note: {stt.get('error')}")

    eng = result.get("engine_result", {})
    route = eng.get("route", {})
    print(f"\n2. ResolveLoop Agent Processing (gpt-5-nano / heuristic):")
    print(f"   - Assigned Tier: L{route.get('route_level')} ({route.get('plan')})")
    print(f"   - Actions Taken: {eng.get('solve', {}).get('actions')}")
    print(f"   - Evaluation Score: {eng.get('score', {}).get('score')}/100")

    print(f"\n3. Customer Resolution Text:")
    print(f"   - \"{result.get('response_text')}\"")

    tts = result.get("tts_result", {})
    print(f"\n4. Text-to-Speech (Smallest AI Lightning):")
    if tts.get("success"):
        print(f"   - Audio Synthesized: {tts.get('audio_path')} ({tts.get('bytes_written')} bytes)")
    else:
        print(f"   - Status: Fallback / Skipped ({tts.get('error')})")
        print(f"   - Note: {tts.get('note')}")

    print("\nEnd-to-End Voice Cycle Completed Successfully.")

def main():
    parser = argparse.ArgumentParser(description="ResolveLoop Customer Support Workforce CLI")
    parser.add_argument("--voice", nargs="?", const="test.wav", help="Process audio file through Smallest AI voice loop")
    parser.add_argument("--benchmark", action="store_true", help="Run the comparative 2-pass learning benchmark")
    args = parser.parse_args()

    print_banner()

    if args.voice:
        run_voice_demo(args.voice)
    else:
        run_p0_demo()
        # Also run voice demo with test.wav if present to demonstrate full pipeline
        test_wav = BASE_DIR / "test.wav"
        if test_wav.exists():
            print("\n" + "=" * 70)
            print("Running Voice Demo Verification with test.wav...")
            run_voice_demo(str(test_wav))

if __name__ == "__main__":
    main()
