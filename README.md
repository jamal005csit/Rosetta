# Rosetta — Record the old app. Get the new one, with proof.

Turns a screen recording of a legacy app into a modern web app and proves parity.

Stack: Python 3.11 FastAPI backend, React Vite TypeScript frontend, Express + better-sqlite3 generated app, Playwright replay, Meta Model API (OpenAI-compatible) isolated in `backend/muse/client.py`.

## Quick demo (7 steps)

1. Configure Meta access: `cp .env.example .env` then set `META_API_BASE=https://api.meta.ai/v1`, `META_API_KEY`, `MUSE_MODEL=muse-spark-1.3`. Offline fallback works with no key.
2. Install backend deps: `python3 -m pip install -r backend/requirements.txt` then `python3 -m pytest backend/tests/test_legacy_rules.py backend/tests/test_selftest.py -v`.
3. Build demo job offline: `mkdir -p jobs/demo && python3 -m backend.tools.run_phase2 --job jobs/demo && python3 -m backend.tools.run_phase3 --job jobs/demo && python3 -m backend.tools.run_phase4 --job jobs/demo`.
4. Run the new app: `cd jobs/demo/generated_app && npm install && npm start` then open `http://127.0.0.1:3000/api/health` and `/api/customers` (seeded from `sample_data`).
5. Run Rosetta API: `uvicorn backend.app.main:app --reload --port 8000` then `POST /jobs` upload, `POST /jobs/{id}/run/{stage}` for ingest observe specify generate replay score repair report.
6. Run Rosetta frontend: `cd frontend && npm install && npm run dev` open `http://127.0.0.1:5173`, upload video, watch live stage progress, open report page, delete job when done.
7. Get proof: open `jobs/demo/report.html`, download `jobs/demo/export.zip` (contains `generated_app/`, `appspec.json`, `report.html`, `MIGRATION_NOTES.md`).

## Legacy app

Staged Tkinter app `legacy_app/app.py`: `CairoTrade Order Entry v3.2 (2004)` with Login, Main menu, Customer lookup, Order entry, Daily report. `F2` saves, `F5` refreshes, `Esc` cancels. Rules in `legacy_app/rules.py`: 5% line discount at qty>=10, 12% at qty>=50, VAT 14% on discounted subtotal, Yes/No warning over credit limit, total rounded to nearest 0.05 EGP. `File > Archive` does nothing (coverage trap).

## Meta API isolation

Only `backend/muse/client.py` talks to Meta. If your endpoint differs, edit the `ADJUST-1..7` markers there: `_endpoint_url`, `_headers`, `_build_video_part`, `_build_image_part`, `_build_payload`, `_parse_usage`, `_parse_content`. Everything else (validation, retries, budget, logging) is provider-agnostic. Prompts live in `backend/prompts/*.md`. Calls log duration+tokens to `jobs/{id}/muse_calls.jsonl` with per-job budget.

## Repo layout

`backend/app/` FastAPI, `backend/muse/` client, `backend/stages/` 1-6, `backend/schemas/`, `backend/export/packager.py`, `frontend/` React app, `legacy_app/`, `jobs/` runtime output.