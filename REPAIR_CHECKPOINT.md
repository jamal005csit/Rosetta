# Rosseta Repair Checkpoint

Last updated: 2026-11-03

## Branch
`repair/rosetta-full-repair` (based on `main`)

## Progress

- [x] Phase 0 — Baseline inspection and acceptance mapping completed.
- [ ] Phase 1 — Backend API integration and job-store correctness/security.
- [ ] Phase 2 — Evidence-based observation and AppSpec generation.
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

## Next action

Start Phase 1 by rereading the current branch files, then fix router mounting and job-store correctness/security. Commit a checkpoint after Phase 1 before moving to Phase 2.
