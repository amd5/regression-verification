import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "release_skill.py"
SPEC = importlib.util.spec_from_file_location("release_skill", SCRIPT_PATH)
release_skill = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(release_skill)


class ReleaseSkillTests(unittest.TestCase):
    def test_next_version_supports_semver_components(self):
        self.assertEqual(release_skill.next_version("1.2.9"), "1.2.10")
        self.assertEqual(release_skill.next_version("1.2.9", "minor"), "1.3.0")
        self.assertEqual(release_skill.next_version("1.2.9", "major"), "2.0.0")
        with self.assertRaises(release_skill.ReleaseError):
            release_skill.next_version("1.2")
        with self.assertRaises(release_skill.ReleaseError):
            release_skill.next_version("1.2.9", "invalid")

    def test_parse_remote_accepts_github_https_and_ssh(self):
        self.assertEqual(release_skill.parse_remote("https://github.com/amd5/example.git"), ("amd5", "example"))
        self.assertEqual(release_skill.parse_remote("git@github.com:amd5/example.git"), ("amd5", "example"))

    def test_bump_version_updates_manifest_and_readmes(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "manifest.json").write_text(
                json.dumps({"name": "example", "version": "2.4.9", "updated_at": "2026-01-01"}, indent=2) + "\n",
                encoding="utf-8",
            )
            (root / "README.md").write_text("当前版本：`2.4.9`\n", encoding="utf-8")
            (root / "README_EN.md").write_text("Current version: `2.4.9`\n", encoding="utf-8")

            old_version, new_version = release_skill.bump_version_files(root, "2026-07-27", "major")

            self.assertEqual((old_version, new_version), ("2.4.9", "3.0.0"))
            manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["version"], "3.0.0")
            self.assertEqual(manifest["updated_at"], "2026-07-27")
            self.assertIn("`3.0.0`", (root / "README.md").read_text(encoding="utf-8"))
            self.assertIn("`3.0.0`", (root / "README_EN.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
