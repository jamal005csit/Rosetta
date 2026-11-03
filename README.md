# Rosetta

**Record a legacy application. Generate a replacement. Verify behavioral parity with evidence.**

Rosetta turns a screen recording of a legacy desktop application into an evidence-backed AppSpec, a generated React application, a real Playwright replay, a weighted parity report, and a ZIP export.

## Requirements

- Windows 10/11 or a recent Linux/macOS environment.
- Python 3.11.
- Node.js 20 LTS or newer, with npm.
- FFmpeg available on `PATH`.
- A configured Muse-compatible API endpoint and API key for observation, AppSpec generation, visual judging, and repair.
- Internet access on first use if `faster-whisper` must download its speech model or npm must install dependencies.

The Muse adapter currently assumes an OpenAI-compatible `/chat/completions` endpoint, Bearer authentication, image input, and strict JSON Schema response formatting. Those provider-specific assumptions must be verified against the actual API account before running a real job.

## Windows PowerShell setup

Run these commands from the repository root.

1. **Install prerequisites.** Install Python 3.11, Node.js 20 LTS, and FFmpeg. Confirm that `py -3.11 --version`, `node --version`, `npm --version`, and `ffmpeg -version` work in a new PowerShell window.

2. **Create the Python environment and install backend dependencies.**

   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   python -m pip install -r backend/requirements.txt
   python -m playwright install chromium
   ```

   If PowerShell blocks virtual-environment activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that PowerShell session, then activate again.

3. **Configure Muse and speech transcription.**

   ```powershell
   Copy-Item .env.example .env
   notepad .env
   ```

   Set `META_API_BASE`, `META_API_KEY`, and `MUSE_MODEL`. Keep the key private. Optional settings are `MAX_CALLS_PER_JOB` (default 50), `JOBS_DIR` (default `jobs`), and `WHISPER_MODEL` (default `tiny`). The backend loads the root `.env` file without overriding variables already set in the process environment.

4. **Start the FastAPI backend** in its own PowerShell terminal.

   ```powershell
   .\.venv\Scripts\Activate.ps1
   uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
   ```

   Check `http://127.0.0.1:8000/health`.

5. **Start the React frontend** in a second PowerShell terminal.

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

   Open `http://127.0.0.1:5173`. The Vite development server proxies API requests to the backend on port 8000.

6. **Upload a recording and run the pipeline.** Create a job by uploading an MP4, MOV, MKV, or WebM screen recording. Open the job and select **Run full pipeline**. Rosetta runs ingest → observe → specify → generate → replay → score → repair → report. A failed stage stops the sequence and displays the backend error; it does not substitute fabricated observations or screenshots.

7. **Inspect and export the result.** Open `report.html` (the parity report) to review each step, browser action, active screen, score component, and linked legacy/replay evidence. Download `export.zip` when the report and generated React build are available.

## Command-line pipeline

The same stages can be run without the frontend. Configure the root `.env` first:

```powershell
.\.venv\Scripts\Activate.ps1
python -m backend.tools.run_phase2 --job jobs/demo --video "C:\recordings\legacy-app.mp4"
python -m backend.tools.run_phase3 --job jobs/demo
python -m backend.tools.run_phase4 --job jobs/demo --max-rounds 3
```

- Phase 2 extracts timestamped keyframes and audio, transcribes speech locally when available, then asks Muse to produce observations and an AppSpec.
- Phase 3 generates React/Vite source and runs the actual app through Playwright. It installs the generated app's npm dependencies if needed; the generated app's `npm start` command builds the Vite bundle and launches the Express server.
- Phase 4 compares real replay evidence, optionally repairs generated source through Muse (maximum three rounds), reruns the full journey, and writes the report.

The command-line stages require the same runtime dependencies as the API pipeline. They are not an offline synthetic demo.

## Running tests

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest backend/tests -v
cd frontend
npm install
npm run build
```

The mock Muse self-test does not require a live API key:

```powershell
cd ..
python -m backend.tools.selftest --mock
```

For an end-to-end acceptance run, use a real recording, a working Muse endpoint/key, FFmpeg, Node/npm, and Playwright Chromium. The mock self-test and unit fixtures do not establish real-recording parity.

## Scoring and repair guarantees

- Per-step score: `0.40 × State + 0.30 × Data + 0.20 × Flow + 0.10 × Visual`.
- Overall parity is the weighted mean across journey steps.
- Pass requires parity ≥ 90% and no weight-2 step below 0.5.
- State, data, and flow checks use the actual browser's active screen, DOM-derived values/text, and successful action result.
- Visual credit requires a successful model comparison of the original and generated screenshots. Missing screenshots, missing judge configuration, or judge failures receive 0.
- Repair patches are limited to existing files under `generated_app/client/src/` and `generated_app/server/`. AppSpec, source recording, tests, scoring logic, and generated distribution output are not patch targets.
- Repair is limited to three rounds. Every round rebuilds, replays the entire journey, and rescores. AppSpec integrity is checked before and after repair.
- Muse retries are schema-validated, count against the persistent per-job budget, and are logged in `jobs/<id>/muse_calls.jsonl`.

## Evidence and data handling

Runtime jobs are stored under `jobs/<id>/` and are excluded from Git. Original uploaded recordings and extracted audio remain in the local job directory; the export deliberately excludes the uploaded video, WAV audio, databases, `node_modules`, caches, and environment secrets. Exports include the generated source/build, AppSpec, observations, parity and repair history, report, keyframes, and browser replay evidence.

Do not commit `.env`, API keys, recordings, or private customer data.

## Legacy application

The staged Tkinter reference app is in `legacy_app/app.py`; deterministic business rules are in `legacy_app/rules.py`. The generator should preserve observed behavior and evidence, not infer unobserved screens or controls.

## Repository layout

- `backend/app/` — FastAPI endpoints, job store, and stage orchestration.
- `backend/muse/` — provider adapter, schema validation, persistent budget, and call logging.
- `backend/stages/` — media ingestion, observation, specification, generation, replay, scoring, repair, and reporting.
- `backend/schemas/` and `backend/prompts/` — structured contracts and model prompts.
- `backend/export/` — evidence-aware ZIP packager.
- `frontend/` — React/Vite job and report interface.
- `legacy_app/` — reference application and deterministic business rules.
- `jobs/` — local runtime artifacts (not committed).

## Verification status

The repair branch includes implementation and regression-test updates. The tests, Windows PowerShell workflow, live Meta endpoint compatibility, Vite build, and real Playwright recording replay still require execution in a network-enabled environment with the required credentials and local prerequisites. Do not treat the acceptance suite as passing until those runs complete.
