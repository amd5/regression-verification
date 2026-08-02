# Output Evaluation

The governed output cases cover changed-file selection, dependency expansion, monolithic-checker splitting, native ownership, UI/design surface inventory, design-source authority, risk-profile separation, and missing external evidence.

Expected behavior:

- coverage is audited before execution;
- focused checks do not replace a required completion or release gate;
- `BLOCKED` and `KNOWN_FAIL` remain non-passing;
- native tests stay in their owning repositories;
- risky verification is routed to explicit evidence profiles.
- UI candidates map exactly once, screenshots do not replace authoritative annotations, and absent browser, original-design, desktop-runtime, or real-device evidence remains `BLOCKED`.

Machine-readable cases are maintained in `evals/output_cases.jsonl`.
