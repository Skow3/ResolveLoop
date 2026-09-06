# ResolveLoop: Manual Execution & Operation Guide

This step-by-step guide explains how to set up, configure, and execute the ResolveLoop workforce manually.

---

## 1. Prerequisites

- Python 3.9 or higher (Python 3.10+ recommended)
- `pip` package manager
- (Optional) Active API keys for OpenAI (`gpt-5-nano`) and Smallest AI (Pulse STT + Lightning TTS)

---

## 2. Dependency Installation

Install the required lightweight runtime dependencies:

```bash
pip install -r requirements.txt
```

*(Core dependencies include `requests`, `python-dotenv`, `typing-extensions`, and standard Python libraries).*

---

## 3. Environment Configuration (`.env`)

Create your `.env` file from the provided template:

```bash
cp .env.example .env
```

Edit `.env` and supply your credentials:

```env
# OpenAI API Key for runtime agent intelligence (Router, L1-L4, Evaluator, Reflection)
OPENAI_API_KEY=your_openai_api_key_here

# Runtime Model (gpt-5-nano)
RESOLVELOOP_MODEL=gpt-5-nano

# Enable OpenAI LLM inference (1 = enabled, 0 = heuristic deterministic fallback)
RESOLVELOOP_USE_LLM=1

# Smallest AI API Key for Voice Layer (Pulse STT & Lightning TTS)
SMALLEST_API_KEY=your_smallest_ai_api_key_here
```

> [!IMPORTANT]
> Never commit `.env` to Git. Verify that `.env` is ignored by running `git status`. It should not appear in untracked files.

---

## 4. Starting the 3-Page Interactive Web Application

Launch the full-fledged demo web app:

```bash
python -m resolve_loop.main --web
# Or directly run:
python -m resolve_loop.web_app
```

Navigate to `http://localhost:5000` in your web browser.

### The 3 Core Pages:
1. **Landing Page (`http://localhost:5000/`)**:
   - Hero banner with tagline: *"Every resolution makes the next one better."*
   - Visual architecture map of the autonomous closed learning loop.
   - Live system status indicators (OpenAI `gpt-5-nano`, Smallest AI Voice).
   - "Start Demo Call" and "Open Support CRM" direct call-to-action buttons.
2. **Demo Voice Call Station (`http://localhost:5000/demo`)**:
   - Simulated customer care call center phone console.
   - Switch active caller persona (Alice - Premium, Bob - Standard, Charlie - Enterprise).
   - Real-time microphone speech capture (transcribed via Smallest AI Pulse STT).
   - Audio response player streaming Smallest AI Lightning TTS generated WAV speech.
   - Text fallback chat input and one-click common support scenario buttons.
   - Real-time Orchestrator HUD: lights up active tier (L1-L4), displays routing source (`gpt-5-nano` or `Experience-Learned`), live router thought plan, tools invoked, auto-escalation alerts, and evaluation scorecard.
3. **Company Support CRM (`http://localhost:5000/crm`)**:
   - Customer account overview with lifetime values, emails, and ticket counts.
   - Live `ExperienceStore` explorer displaying accumulated case reflections (`data/experiences.json`).
   - Procedural memory rule inspector (`data/memories.json`).
   - One-click interactive "Run Learning Benchmark" modal demonstrating Pass 1 (Cold) vs Pass 2 (Warm) improvements.

---

## 5. Running the P0 Learning Loop Benchmark via CLI

Execute the full 2-pass comparative learning benchmark from the terminal:

```bash
python -m resolve_loop.main
```

### What this does:
1. **Pass 1 (Cold Start)**: Reads cases from `data/cases.json` without prior memory. Evaluator scores each case and reflection synthesizes operational rules.
2. **Pass 2 (Warm Start)**: Re-runs cases with `ExperienceStore` and `procedural_memory` active. Router adapts routing levels based on prior lessons.
3. **Summary Dashboard**: Compares Pass 1 vs Pass 2 metrics, showing escalation reduction and score improvements.
4. **Voice Demonstration**: Automatically processes `test.wav` through Pulse STT, ResolveLoop, and Lightning TTS.

---

## 5. Running the Smallest AI Voice Pipeline

To process a specific customer audio recording through the voice layer:

```bash
python -m resolve_loop.main --voice test.wav
```

### Execution Flow:
1. **Pulse STT**: Sends `test.wav` audio to Smallest AI Pulse endpoint (`language=en`).
2. **ResolveLoop Ingestion**: Creates support case from transcribed text.
3. **Reasoning & Actions**: Dispatches to `gpt-5-nano` and appropriate support tier (L1-L4).
4. **Lightning TTS**: Synthesizes the customer response text into speech audio.
5. **Output**: Saves generated audio to `data/voice_responses/voice_response_*.wav`.

---

## 6. Testing the Resilient Voice Fallback

To verify that ResolveLoop continues to resolve customer issues even if the voice API is unavailable:

```bash
SMALLEST_API_KEY="" python -m resolve_loop.main --voice test.wav
```

### Expected Behavior:
- Non-fatal notice: `Voice output skipped. Text resolution delivered successfully.`
- Resolution is generated and printed to console.
- Zero crashes; system exits with status code `0`.

---

## 7. Running the Automated Test Suite

Run all unit tests:

```bash
python -m unittest discover tests
```

Expected output:
```
.......
----------------------------------------------------------------------
Ran 7 tests in ~2.2s

OK
```

---

## 8. Inspected Data & Output Artifacts

* **`data/cases.json`**: Input customer support cases.
* **`data/experiences.json`**: Accumulated memory records with descriptions, routing levels, tool traces, scores, and reflections.
* **`data/memories.json`**: Persistent memory store containing `customer_memory`, `case_memory`, `procedural_memory`, and `failure_memory`.
* **`data/voice_responses/`**: Synthesized audio responses produced by Smallest AI Lightning TTS.

---

## 8. Maximor Finance Database Setup & Seeding

1. Ensure PostgreSQL is active and `DATABASE_URL` is configured in `.env`:
   ```env
   DATABASE_URL=postgresql:///maximor_finance
   ```
2. Populate the 14 relational tables with synthetic finance records across Revenue, Cash, AR, AP, and Close:
   ```bash
   python -m resolve_loop.seeds
   ```
3. Run the complete automated test suite (11 unit tests):
   ```bash
   python -m unittest discover tests
   ```
4. Start the Maximor AI web application:
   ```bash
   python -m resolve_loop.main --web --port 5000
   ```
5. In the web interface:
   - Toggle Dark/Light mode using the top-right button.
   - Select caller **Alice Morgan** and click the large central **CALL** button.
   - Listen to the Smallest AI greeting: *"Thanks for calling Maximor AI. Hi Alice Morgan, how can I help you today?"*.
   - Speak hands-free (or click prompt: *"Why was our payment PMT-8821 short on invoice INV-4471?"*).
   - Review the L1 -> L2 auto-escalation, policy `SHORT-PAY-01` discount validation, and synthesized response.
   - Click the 👍 Thumbs Up button to record feedback and update experience confidence!
