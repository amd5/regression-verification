#!/usr/bin/env python3
"""Validate, version, commit, push, and verify a GitHub skill release."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
REMOTE_RE = re.compile(
    r"^(?:https://github\.com/|git@github\.com:)([^/]+)/([^/]+?)(?:\.git)?$",
    re.IGNORECASE,
)
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
)


class ReleaseError(RuntimeError):
    pass


def run(command: list[str], *, cwd: Path = ROOT, capture: bool = False) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=capture,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "command failed").strip()
        raise ReleaseError(f"{' '.join(command)}: {detail}")
    return result.stdout.strip() if capture else ""


def git(*args: str, capture: bool = False) -> str:
    return run(["git", *args], capture=capture)


def parse_remote(remote_url: str) -> tuple[str, str]:
    match = REMOTE_RE.fullmatch(remote_url.strip())
    if not match:
        raise ReleaseError("origin must be a github.com HTTPS or SSH repository")
    return match.group(1), match.group(2)


def next_version(version: str, bump: str = "patch") -> str:
    match = SEMVER_RE.fullmatch(version)
    if not match:
        raise ReleaseError(f"manifest version is not SemVer: {version}")
    major, minor, patch = (int(value) for value in match.groups())
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    if bump == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ReleaseError(f"unsupported version bump: {bump}")


def replace_once(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise ReleaseError(f"could not update {label}")
    return updated


def bump_version_files(root: Path, release_date: str, bump: str = "patch") -> tuple[str, str]:
    manifest_path = root / "manifest.json"
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    old_version = str(manifest_data["version"])
    new_version = next_version(old_version, bump)

    manifest = manifest_path.read_text(encoding="utf-8")
    manifest = replace_once(
        manifest,
        rf'("version"\s*:\s*"){re.escape(old_version)}(")',
        rf"\g<1>{new_version}\g<2>",
        "manifest version",
    )
    manifest = replace_once(
        manifest,
        r'("updated_at"\s*:\s*")\d{4}-\d{2}-\d{2}(")',
        rf"\g<1>{release_date}\g<2>",
        "manifest updated_at",
    )
    manifest_path.write_text(manifest, encoding="utf-8", newline="\n")

    readme_updates = {
        root / "README.md": (f"当前版本：`{old_version}`", f"当前版本：`{new_version}`"),
        root / "README_EN.md": (f"Current version: `{old_version}`", f"Current version: `{new_version}`"),
    }
    for path, (old_marker, new_marker) in readme_updates.items():
        content = path.read_text(encoding="utf-8")
        if content.count(old_marker) != 1:
            raise ReleaseError(f"could not update version marker in {path.name}")
        path.write_text(content.replace(old_marker, new_marker), encoding="utf-8", newline="\n")

    return old_version, new_version


def changed_paths() -> list[Path]:
    tracked = git("diff", "--name-only", "-z", "HEAD", capture=True)
    untracked = git("ls-files", "--others", "--exclude-standard", "-z", capture=True)
    names = {name for name in (tracked + "\0" + untracked).split("\0") if name}
    return [ROOT / name for name in sorted(names)]


def sensitive_findings(paths: list[Path]) -> list[str]:
    findings: list[str] = []
    forbidden_suffixes = {".key", ".pem", ".p12", ".pfx"}
    forbidden_names = {".env", "id_rsa", "id_ed25519", "credentials.json"}
    for path in paths:
        name = path.name.lower()
        if name in forbidden_names or path.suffix.lower() in forbidden_suffixes:
            findings.append(f"sensitive filename: {path.relative_to(ROOT)}")
            continue
        if not path.is_file():
            continue
        data = path.read_bytes()
        if b"\x00" in data:
            continue
        text = data.decode("utf-8", errors="ignore")
        if any(pattern.search(text) for pattern in SECRET_PATTERNS):
            findings.append(f"credential-like content: {path.relative_to(ROOT)}")
    return findings


def validate_repository() -> tuple[str, str, str]:
    root = Path(git("rev-parse", "--show-toplevel", capture=True)).resolve()
    if root != ROOT:
        raise ReleaseError(f"script root {ROOT} is not Git root {root}")
    if any((ROOT / ".git" / marker).exists() for marker in ("MERGE_HEAD", "rebase-merge", "rebase-apply")):
        raise ReleaseError("a merge or rebase is already in progress")
    branch = git("branch", "--show-current", capture=True)
    if branch != "main":
        raise ReleaseError(f"release must run from main, current branch is {branch or 'detached HEAD'}")
    owner, repository = parse_remote(git("remote", "get-url", "origin", capture=True))
    return owner, repository, branch


def run_checks(skill_name: str) -> None:
    run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"])
    if skill_name != "regression-verification":
        raise ReleaseError(f"unexpected package name: {skill_name}")
    run([sys.executable, "-B", str(ROOT / "scripts" / "regression_verification.py"), "--help"])
    git("diff", "--check")


def release_exists(owner: str, repository: str, tag: str) -> bool:
    url = f"https://api.github.com/repos/{owner}/{repository}/releases/tags/{tag}"
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "skill-release"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status == 200
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return False
        raise ReleaseError(f"GitHub Release lookup failed: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise ReleaseError(f"GitHub Release lookup failed: {exc.reason}") from exc


def wait_for_release(owner: str, repository: str, tag: str, timeout_seconds: int) -> None:
    deadline = time.monotonic() + timeout_seconds
    while True:
        if release_exists(owner, repository, tag):
            return
        if time.monotonic() >= deadline:
            raise ReleaseError(
                f"GitHub Release {owner}/{repository}@{tag} was not readable within {timeout_seconds} seconds"
            )
        time.sleep(10)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--message", help="focused Git commit message")
    parser.add_argument(
        "--bump",
        choices=("patch", "minor", "major"),
        default="patch",
        help="semantic version component to increment",
    )
    parser.add_argument("--dry-run", action="store_true", help="run checks without changing version or Git state")
    parser.add_argument("--verify-release", metavar="TAG", help="only verify an already-pushed GitHub Release")
    parser.add_argument("--wait-seconds", type=int, default=300, help="GitHub Release wait timeout")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        owner, repository, branch = validate_repository()
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        skill_name = str(manifest["name"])

        if args.verify_release:
            wait_for_release(owner, repository, args.verify_release, args.wait_seconds)
            print(json.dumps({"repository": f"{owner}/{repository}", "release": args.verify_release, "verified": True}))
            return 0

        paths = changed_paths()
        if not paths:
            raise ReleaseError("no skill changes are available to publish")
        findings = sensitive_findings(paths)
        if findings:
            raise ReleaseError("; ".join(findings))

        run_checks(skill_name)
        if args.dry_run:
            current = str(manifest["version"])
            print(
                json.dumps(
                    {
                        "repository": f"{owner}/{repository}",
                        "checks": "passed",
                        "next_version": next_version(current, args.bump),
                    }
                )
            )
            return 0
        if not args.message or not args.message.strip():
            raise ReleaseError("--message is required unless --dry-run or --verify-release is used")

        git("pull", "--rebase", "--autostash", "origin", branch)
        if not changed_paths():
            raise ReleaseError("no skill changes remain after synchronizing origin/main")
        old_version, new_version = bump_version_files(ROOT, date.today().isoformat(), args.bump)
        paths = changed_paths()
        findings = sensitive_findings(paths)
        if findings:
            raise ReleaseError("; ".join(findings))
        run_checks(skill_name)

        tag = f"v{new_version}"
        if git("tag", "--list", tag, capture=True):
            raise ReleaseError(f"local tag already exists: {tag}")
        if git("ls-remote", "--tags", "origin", f"refs/tags/{tag}", capture=True):
            raise ReleaseError(f"remote tag already exists: {tag}")

        git("add", "--all", "--", ".")
        git("diff", "--cached", "--check")
        git("commit", "-m", args.message.strip())
        git("tag", "-a", tag, "-m", f"{skill_name} {tag}")
        git("push", "--atomic", "origin", f"HEAD:refs/heads/{branch}", f"refs/tags/{tag}")
        wait_for_release(owner, repository, tag, args.wait_seconds)
        print(
            json.dumps(
                {
                    "repository": f"{owner}/{repository}",
                    "branch": branch,
                    "previous_version": old_version,
                    "version": new_version,
                    "tag": tag,
                    "commit": git("rev-parse", "HEAD", capture=True),
                    "release_verified": True,
                }
            )
        )
        return 0
    except (OSError, ValueError, ReleaseError, json.JSONDecodeError) as exc:
        print(f"release failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
