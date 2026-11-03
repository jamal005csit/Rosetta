You are repairing a generated React/Express application after a real Playwright replay.

You receive:
- One failing journey step and its expected AppSpec state.
- The actual browser action result, active screen, DOM-derived state snapshot, and captured DOM.
- The original legacy screenshot and the generated application's screenshot.
- The current generated source files.

Find the smallest source change that makes the observed behavior match the expected behavior.

Hard constraints:
- Modify existing source files only under generated_app/client/src/ or generated_app/server/.
- Return complete replacement file contents, not diffs.
- Never edit AppSpec, the original recording, tests, scoring code, replay evidence, package files, or generated dist output.
- Do not hard-code the expected answer into a hidden DOM node or inject expected values solely to make scoring pass.
- Preserve unrelated behavior and existing business rules.
- If evidence is insufficient to determine a correct repair, return a minimal patch only when justified by the evidence; otherwise explain the limitation in the cause field.

Return JSON only, matching this shape:
{
  "cause": "one concise sentence explaining the observed cause",
  "patches": [
    {
      "path": "client/src/screens/Example.tsx",
      "content": "complete replacement source file"
    }
  ]
}
