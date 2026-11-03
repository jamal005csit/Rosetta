# Rosseta Repair Checkpoint

Last updated: 2026-11-03

## Branch
`repair/rosetta-full-repair` (based on `main`)

## Progress

- [x] Phase 0 — Baseline inspection and acceptance mapping completed.
- [x] Phase 1 — Backend API integration and job-store correctness/security (implementation complete; runtime tests pending).
- [x] Phase 2 — Evidence-based observation and AppSpec generation (implementation complete; runtime tests pending).
- [x] Phase 3 — Real React/Vite application build and serving (implementation complete; runtime tests pending).
- [x] Phase 4 — Genuine Playwright replay and parity scoring (implementation complete; runtime tests pending).
- [x] Phase 5 — Genuine Muse-driven repair, limited to generated_app (implementation complete; runtime tests pending).
- [x] Phase 6 — Muse schema validation, retries, budgets, and logging (implementation complete; runtime tests pending; provider compatibility unverified).
- [x] Phase 7 — Frontend workflow, report, and ZIP export (implementation complete; runtime tests pending).
- [x] Phase 8 — Acceptance tests AT01–AT15 and Windows setup documentation (implementation and static audit complete; execution pending).

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

## Phase 3 implementation checkpoint

- Removed the hand-authored `dist/index.html` imitation from generation.
- Vite now uses `generated_app/client` as its root and builds the React application into `generated_app/dist`.
- The generated package's `npm start` runs the Vite production build before starting Express, on Windows and Unix-compatible shells.
- Express serves only the actual Vite `dist` output; it no longer serves raw TypeScript source as a fallback and returns HTTP 503 with a clear instruction if the build is absent.
- Kept API endpoints separate from static frontend serving and added basic order payload validation.
- Updated generator tests to assert the real Vite entrypoint/build configuration and the absence of the fabricated distribution HTML.

**Verification status:** source and tests are committed, but npm install/build and the test suite have not been run because a local repository checkout is unavailable in this environment.

## Next action

Proceed to Phase 4: remove fabricated Playwright/replay evidence and make parity scoring depend on real browser execution, real screenshots, and actual DOM/application state.


## Phase 8 implementation checkpoint

- Replaced the obsolete offline-demo instructions with a Windows PowerShell setup and real pipeline workflow.
- Documented Python 3.11, Node/npm, FFmpeg, Playwright Chromium, Muse credentials, local Whisper model, CLI usage, API/frontend startup, tests, scoring, repair limits, and export contents.
- Added root `.env` loading with process-environment precedence and documented all supported environment settings.
- Updated CLI tools so they no longer call removed synthetic fallbacks; model-dependent phases require Muse configuration.
- Updated Makefile test targets, pytest discovery configuration, README checks, and Git ignore rules for secrets/runtime artifacts.
- Tightened report/export prerequisites so a report cannot be generated without a real AppSpec and parity result, and an export cannot be created without a built React app and parity artifact.
- Made report screenshot links portable: they work through the live API and relative to the exported ZIP.
- Performed a static cross-file audit of stage orchestration, schemas, job lifecycle, evidence paths, scoring, repair boundaries, frontend calls, report links, and export exclusions.

## Final verification state

- All eight repair phases have implementation checkpoints committed on `repair/rosetta-full-repair`.
- The branch comparison reports **111 commits ahead of `main`, 0 behind** at checkpoint refresh. The `main` branch was not modified.
- GitHub file operations and commits succeeded.
- Added a Windows GitHub Actions verification workflow at `.github/workflows/windows-verification.yml` to run Python compilation, backend tests, Playwright Chromium installation, frontend dependency installation/build, and the mock self-test on a Windows runner.
- The first Windows CI run exposed five regressions. Four were corrected: the generated JSX active-screen attribute escaping, data-value matching, Windows short-path preservation in repair validation, and README setup/output documentation.
- The next CI run passed 31 tests and isolated two remaining failures: Menu and Report templates did not preserve the exact AppSpec field IDs. The generator was updated to derive those test IDs from each screen's AppSpec fields.
- **Current verification run:** GitHub Actions run [#41595329418](https://github.com/jamal005csit/Rosseta/actions/runs/41595329418) is still in progress. Its test/build results are not yet available. The latest prior completed run reported 31 passed and 2 failed before the AppSpec field-ID mapping fix.
- Python compilation, dependency installation, and Playwright Chromium installation succeeded in the preceding Windows CI run. Frontend build and mock self-test were skipped because pytest failed first.
- **Still not verified:** a clean full backend test run after the latest generator fix, TypeScript/Vite compilation, the mock self-test, FFmpeg extraction/timestamp mapping, faster-whisper transcription, real recording replay, and live Meta endpoint compatibility.
- The local checkout attempt could not resolve `github.com`; Windows GitHub Actions now provides the runtime environment for automated checks. Do not claim tests or builds passed until the current run succeeds.
- Before merging, require a green Windows verification run and execute one real recording end-to-end with a valid Muse endpoint/key; confirm actual screenshots, parity, repair history, report, and ZIP.

## Resume point

1. Monitor Windows Actions run [#41595329418](https://github.com/jamal005csit/Rosseta/actions/runs/41595329418).
2. If it fails, inspect the failed job log and fix the exact regression on this branch; add a checkpoint after each fix.
3. If it passes, record the pytest count, frontend build, and mock self-test results here.
4. Then run one real recording through the full pipeline with valid Muse credentials and FFmpeg; provider compatibility and actual parity remain acceptance requirements.
5. Open a pull request for review only after automated checks pass. Do not merge to `main` until real-recording verification passes.
