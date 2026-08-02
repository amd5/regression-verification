# regression-verification

Current version: `2.0.5`

Repository: <https://github.com/amd5/regression-verification>

## Overview

`regression-verification` is a governed skill for Codex, Claude Code, Agent Skills, and other coding agents. It builds, maintains, audits, selects, and executes modular regression gates across one or more related repositories. After the final file write, the agent automatically runs the authoritative completion entrypoint declared by the project without waiting for a user reminder, and reruns it after any later write.

Verification is organized by business module rather than repository. Native language and platform tests stay in their owning repositories. The shared regression center discovers, selects, orders, executes, classifies, and records them without duplicating test implementation.

## Capabilities

- Reuse an existing project-owned `regression/` center and its local contract.
- Maintain repositories, modules, trigger paths, dependencies, checks, profiles, and native-test inventory.
- Select modules from worktree, staged, untracked, and optional default-branch differences.
- Split monolithic checkers through stable check IDs and module mappings.
- Audit tools, scripts, and native verification entrypoints for missing, duplicate, empty, or unreferenced coverage.
- Audit UI surfaces, approved design sources, states, viewports, screenshot evidence, components, styles, and visual runtime gates.
- When explicitly authorized, scan the complete Codex history scope and promote a file, concrete module, or real UI surface only after at least three complete write-user-correction-write cycles.
- Separate completion, full, release, runtime, migration, real-device, and post-release gates.
- Preserve exact `PASS`, `FAIL`, `BLOCKED`, `KNOWN_FAIL`, and `SKIPPED` semantics.
- Require isolation, restoration, and zero-residue evidence for databases, Redis, queues, and temporary files.

## When To Use

- Before completing development, bug fixes, or refactors.
- For cross-repository API, configuration, state, protocol, or command changes.
- When new fields, scripts, tools, migrations, or test entrypoints need durable regression coverage.
- When a large contract checker must become selectively executable by business module.
- When authorized history or repository audits reveal missing regression checks.
- When repeated Codex mistakes and user-requested restorations must become durable program or UI regression checks.
- When UI, layout, component, style, design-source, or screenshot changes need automated, runtime, and real-device evidence.
- Before release builds, runtime interoperability, real-device acceptance, or production readback.

Do not trigger it for status-only or explanation-only requests, tasks that explicitly prohibit verification, or discussion with no implementation scope.

## Workflow

1. Register requirements, project rules, related repositories, and risk boundaries.
2. Discover existing tests, tools, scripts, documentation checks, and the regression center.
3. Map trigger paths, transitive dependencies, and stable check IDs by business module.
4. Audit manifests, references, command arrays, inventory, known-failure expiry, and any UI/design or privacy-safe Codex-rework inventory.
5. For authorized Codex history, scan the entire scope and promote only targets with at least three complete cycles.
6. Run focused modules during implementation. After the final file write, automatically execute the project-declared completion entrypoint and rerun it after any later write; when the project declares none, use changed + completion. Use full, release, and explicit evidence profiles when required.
7. Close every requirement with fresh evidence. Never convert blocked or known-failure outcomes into a pass.

## Deterministic Tool

Audit a standard JSON regression center:

```powershell
python scripts/regression_verification.py audit --root D:\path\to\project
```

Build a validated command without executing it:

```powershell
python scripts/regression_verification.py run --root D:\path\to\project --changed --profile completion
```

Execute the project-owned runner:

```powershell
python scripts/regression_verification.py run --root D:\path\to\project --changed --profile completion --execute
```

Focused and full examples:

```powershell
python scripts/regression_verification.py run --root D:\path\to\project --module api-contract --profile completion --execute
python scripts/regression_verification.py run --root D:\path\to\project --all --profile full --execute
```

The helper only recognizes `regression/run.php`, `run.py`, `run.ps1`, or `run.sh` under the selected project root. It never evaluates arbitrary shell strings from manifests. The project-owned runner and framework tests remain authoritative for execution behavior.

## Safety

- Never duplicate or rewrite native tests inside the coordinator or skill.
- Never scan private Codex conversations unless the user explicitly authorizes a complete scope.
- Never count injected project rules, technical rollback contracts, operational recovery, two-cycle rework, or test/tool/asset categories as a real repeated UI regression; never commit raw messages, commands, credentials, or full session/task IDs.
- Never auto-run production writes, migrations, node control, credentialed operations, or device acceptance.
- Never report missing dependencies, authority, environment, or external evidence as success.
- Never substitute a build or component test for required browser, original-design, screenshot, interaction, or real-device evidence, and never infer authoritative layout values from screenshots.
- Never broaden known failures, delete assertions, or skip required suites to obtain a green result.
- Never publish target-project reports, credentials, environment files, or business repository content with the skill.

## Installation

PowerShell:

```powershell
$skillsRoot = Join-Path $env:USERPROFILE ".codex\skills"
git clone https://github.com/amd5/regression-verification.git (Join-Path $skillsRoot "regression-verification")
```

Bash:

```bash
git clone https://github.com/amd5/regression-verification.git \
  "$CODEX_HOME/skills/regression-verification"
```

Example invocation:

```text
Use $regression-verification to audit changed-file coverage and run the completion gate across all related repositories.
```

## Maintainer Release

Every package change must pass tests, update the version, commit, atomically push `main` and the version tag, and verify the GitHub Release:

```powershell
python scripts/release_skill.py --message "describe this skill update"
```

Use `--bump major` for incompatible migrations. See `references/release-workflow.md` for the complete gate.

## Layout

```text
regression-verification/
  SKILL.md
  README.md
  README_EN.md
  manifest.json
  agents/
  references/
  scripts/
  tests/
  evals/
  security/
  reports/
```

## License

See `LICENSE`.
