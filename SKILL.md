---
name: regression-verification
description: Build, audit, select, and execute modular regression across related repositories before coding work is complete. Automatically run a project-declared completion entrypoint after the final file write without waiting for a user reminder, and rerun it after any later write. Use for completion and release gates, changed-file selection, coverage audits, checker splits, native test or tool catalogs, cross-repository contracts, UI or visual design-source regression, authorized Codex rework-history promotion, and maintenance of regression-verification itself. Preserve native tests and exact PASS, FAIL, BLOCKED, and KNOWN_FAIL semantics. Exclude status-only, explanation-only, and explicit no-verification or no-write requests.
---

# Regression Verification

Turn project changes into repeatable, evidence-backed regression gates.

## Workflow

1. Register requirements and repository rules; use requirement-closure for cross-repository or three-plus-item work.
2. Discover related repositories, native verification entrypoints, and the existing `regression/` center. Model by business module and keep native tests in their owning repositories. Read [architecture.md](references/architecture.md) and [coverage-audit.md](references/coverage-audit.md).
3. Map changed code, contracts, docs, migrations, tools, and tests to triggers, dependencies, checks, profiles, and evidence. For UI or design work, read [ui-design.md](references/ui-design.md) and map each surface exactly once.
4. When the user explicitly authorizes Codex history, read [codex-rework.md](references/codex-rework.md), scan the complete authorized scope without sampling, and promote only targets with at least three independent complete write-correction-write cycles. Keep raw history and local cache out of Git.
5. Run `python scripts/regression_verification.py audit --root <project-root>` for the standard JSON layout. Fix every structural, reference, inventory, command, cycle, known-failure, UI-surface, or Codex-rework inventory error.
6. Preserve authoritative checkers through stable IDs. Register every native entrypoint or classify it as runtime, migration, real-device, post-release, forbidden, or obsolete.
7. After the final file write, automatically execute the exact completion entrypoint declared by the project without asking the user to run it. Rerun it after any later in-scope write. When no project-specific entrypoint exists, run changed + completion through `python scripts/regression_verification.py run --root <project-root> --changed --profile completion --execute`; add `--base default` for committed branch differences, and use full or release when required.
8. Apply [execution-and-results.md](references/execution-and-results.md), re-read requirements, and use verification-before-completion. Report modules, checks, statuses, reports, blockers, and residual risk; focused evidence never replaces a required full gate.

Use `scripts/regression_verification.py --help` for deterministic audit and execution syntax. Re-run `evals/` when trigger, coverage, execution, or result boundaries change.

## Safety Boundary

- Never copy native tests or execute manifest shell strings; command arrays and the project runner remain authoritative.
- Do not auto-run migration, production, deployment, node-control, credentialed, or real-device checks without project authority. Stateful checks must isolate, restore, and prove zero residue.
- Missing prerequisites or evidence are `BLOCKED`. Known failures need an exact fingerprint, owner, reason, and unexpired date and still block completion.
- Screenshots cannot override authoritative design annotations; builds and component tests cannot replace required visual, interaction, or device evidence.
- Scan Codex history only when explicitly authorized, then assess the full authorized scope without sampling.

## Maintainer Release Gate

For any package change, run `python scripts/release_skill.py --message "<focused commit message>"` after tests and diff review. Breaking renames use `--bump major`. Completion requires atomic `main` and version-tag push plus a readable GitHub Release. Follow [release-workflow.md](references/release-workflow.md); this gate publishes only the skill repository.
