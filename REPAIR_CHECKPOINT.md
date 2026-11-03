# Rosseta Repair Checkpoint

Last updated: 2026-11-03

## Branch
`repair/rosetta-full-repair` (based on `main`)

## Progress

- [x] Phase 0 — Baseline inspection and acceptance mapping completed.
- [x] Phase 1 — Backend API integration and job-store correctness/security (implementation complete; runtime tests pending).
- [x] Phase 2 — Evidence-based observation and AppSpec generation (implementation complete; runtime tests pending).
- [ ] Phase 3 — Real React/Vite application build and serving.
- [ ] Phase 4 — Genuine Playwright replay and parity scoring.
- [ ] Phase 5 — Genuine Muse-driven repair, limited to generated_app.
- [ ] Phase 6 — Muse schema validation, retries, budgets, and logging.
- [ ] Phase 7 — Frontend workflow, report, and ZIP export.
- [ ] Phase 8 — Acceptance tests AT01–AT15 and Windows setup documentation.

## Phase 0 findings carried forward

1. The API entry point appears to mount an incomplete router, leaving later pipeline stages inaccessible.
2. Stage 4 creates a React/Vite app but also emits a separate static HTML imitation that is served instead of the React build.
3. Observation fallback can fabricate a fixed journey unrelated to the supplied recording; audio transcription is absent.
4. Replay/scoring fallbacks can fabricate screenshots and DOM evidence; data checks inspect injected expected values rather than rendered application state.
5. Visual scoring can default to a passing-looking value without actual visual comparison.
6. Repair logic edits generated distribution HTML with expected values instead of performing a genuine constrained code repair.
7. Muse call paths have inconsistent schema validation, retry/budget accounting, and failure logging.
8. AppSpec evidence/timestamp constraints and coverage claims need stricter enforcement.
9. Demo setup order and browser installation instructions are incorrect/incomplete.
10. Job-store lookup appears capable of creating directories for nonexistent jobs; job IDs need validation.
11. Tests need to verify real behavior, not merely artifact presence.

## Repair invariants

- Do not weaken acceptance criteria or fabricate observations, screenshots, DOM, scores, or repair results.
- Preserve the deterministic legacy business rules.
- Keep all automated repairs confined to `generated_app/`.
- Enforce a maximum of three repair rounds.
- Preserve the scoring formula: 0.4 State + 0.3 Data + 0.2 Flow + 0.1 Visual; pass threshold 90%, with no weight-2 step below 0.5.
- Keep `main` untouched; work and checkpoint on this repair branch.
- Mark a phase complete only after its changes and relevant checks are complete. Record test limitations explicitly.

## Phase 1 implementation checkpoint

- Mounted the complete stage router, exposing ingest through report.
- Changed API reads/stage execution to use non-creating job lookup; nonexistent jobs now return 404 instead of creating directories.
- Added strict 12-character lowercase hexadecimal job ID validation and resolved-path containment checks.
- Updated job listing/deletion to operate only on valid job IDs.
- Added upload cleanup if writing the uploaded video fails and streamed uploads in bounded chunks.
- Expanded the stage model to include repair and report.
- Added regression coverage for nonexistent and malformed job IDs.
- Corrected the event stream framing while keeping it bounded for existing clients.

**Verification status:** source changes and regression tests are committed. Tests have not been executed: the available runtime could not resolve github.com for a repository clone, and the GitHub connection exposes file operations but no local test runner. Do not treat the suite as passing until it is run in a network-enabled checkout.

## Phase 2 implementation checkpoint

- Removed the production hard-coded observation journey. Without a configured Muse client, observation now fails clearly instead of fabricating actions.
- Removed the production hard-coded AppSpec fallback and stopped normalizing missing evidence, inventing legacy frame paths, or inserting an unobserved Archive menu item.
- Added chronological/unique timestamp checks for observations.
- Added timestamp-linked frame extraction metadata using ffmpeg `showinfo`; observation results are associated with the nearest real frame only when it is within three seconds.
- Added local `faster-whisper` transcription support (CPU/int8, configurable `WHISPER_MODEL`, default `tiny`) when an audio stream exists. If transcription support is unavailable, the transcript remains explicitly empty and a warning is logged.
- AppSpec generation now requires a Muse client, validates observation input, requires screen/field/shortcut/flow/rule evidence timestamps to match actual observation timestamps, checks referenced screens and targets, and requires each journey frame to exist and be attached to an observation.
- Updated schemas and prompts to require screen-level evidence and exact frame references.
- Reworked tests to use explicit test-only fixtures rather than calling production fallback generators.

**Verification status:** regression tests were updated/added but have not been executed. Local checkout remains blocked by DNS resolution for github.com; the connected GitHub service supports source edits but not test execution. Frame timestamp extraction and faster-whisper model download/transcription remain runtime verification items.

## Next action

Proceed to Phase 3: inspect the generated React/Vite app and server, then remove the static HTML imitation and serve the actual production Vite build. Keep runtime-verification limitations explicit.
