# Permission Policy

The local user approved the bounded capabilities below for this governed skill on `2026-08-02`, expiring `2027-08-02`.

- `file_read`: project-owned regression manifests, native-test and UI/design inventories, known-failure records, related repository paths, and applicable project instructions in the active task.
- `file_write`: only the skill release script's version markers and focused commit inside this skill repository.
- `subprocess`: only a detected project-owned `regression/run.php`, `run.py`, `run.ps1`, or `run.sh` with validated mode, module, profile, and base arguments. The helper does not evaluate shell strings or choose an executable from a manifest.
- `network`: only the configured GitHub origin and public GitHub Releases API used by `scripts/release_skill.py` for the explicitly requested skill release.

The deterministic helper itself does not edit target projects. A project runner may create its own ignored reports or execute checks allowed by the selected project profile. Migration, production, deployment, node-control, credentialed, and real-device profiles still require the authority and prerequisites defined by the target project.

UI/design inventory auditing reads only project-owned metadata. Browser sessions, original design files, screenshots and real-device evidence remain under the target project's runtime or device authority and are never auto-collected by the deterministic helper.

The machine-readable scope and evidence paths are maintained in `security/permission_policy.json`.
