# Trigger Evaluation

Positive families:

- coding completion regression gates;
- automatic project-declared completion entrypoints after the final file write;
- changed-file module selection;
- monolithic checker splitting;
- full repository and tools coverage audits;
- cross-repository contract closure;
- full, release, runtime, device, migration, and post-release gates;
- UI, visual, approved-design-source, viewport, and screenshot regression;
- authorized privacy-safe Codex rework promotion;
- maintenance and release of the skill itself.

Negative and near-neighbor families:

- status-only and explanation-only requests;
- explicit no-verification or no-write instructions;
- brainstorming without implementation;
- focused test requests that do not claim full completion;
- production advice without action authority.

Machine-readable cases are maintained in `evals/trigger_cases.json` and `evals/trigger-cases.jsonl`.

Latest deterministic semantic evaluation: threshold `0.2`, 10/10 positive triggers, 4/4 exclusions, and 3/3 near neighbors passed, with zero false positives and zero false negatives. The UI/design family covers approved design sources, annotations, viewport and screenshot regression without weakening status-only or no-action exclusions.
