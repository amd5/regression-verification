import json
import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class SkillPackageTests(unittest.TestCase):
    def test_identity_is_consistent(self):
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        openai = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        interface = (ROOT / "agents" / "interface.yaml").read_text(encoding="utf-8")
        readmes = (
            (ROOT / "README.md").read_text(encoding="utf-8"),
            (ROOT / "README_EN.md").read_text(encoding="utf-8"),
        )

        self.assertEqual(manifest["name"], "regression-verification")
        self.assertRegex(skill, r"(?m)^name: regression-verification$")
        self.assertIn('display_name: "回归验证"', openai)
        self.assertIn("$regression-verification", openai)
        self.assertIn('display_name: "回归验证"', interface)
        self.assertIn("$regression-verification", interface)
        expected_repository = f"https://github.com/amd5/{manifest['name']}.git"
        for readme in readmes:
            repository_urls = re.findall(r"https://github\.com/amd5/[^\s)]+\.git", readme)
            self.assertTrue(repository_urls)
            self.assertEqual(set(repository_urls), {expected_repository})

    def test_skill_references_exist(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        references = re.findall(r"\[[^]]+\]\((references/[^)]+)\)", skill)
        self.assertGreaterEqual(len(references), 4)
        for relative in references:
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_evaluation_files_are_valid_json(self):
        json.loads((ROOT / "evals" / "trigger_cases.json").read_text(encoding="utf-8"))
        json.loads((ROOT / "evals" / "semantic_config.json").read_text(encoding="utf-8"))
        for path in (ROOT / "evals").glob("*.jsonl"):
            lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertTrue(lines, path.name)
            for line_number, line in enumerate(lines, 1):
                with self.subTest(path=path.name, line=line_number):
                    json.loads(line)

    def test_project_completion_entrypoint_is_automatic(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        openai = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        execution = (ROOT / "references" / "execution-and-results.md").read_text(encoding="utf-8")

        self.assertIn("Automatically run a project-declared completion entrypoint", skill)
        self.assertIn("automatically execute the project-declared completion entrypoint", openai)
        self.assertIn("无需用户提醒自动执行项目声明的权威完工入口", execution)

    def test_package_has_no_cross_skill_dependency(self):
        forbidden = (
            "requirement-closure",
            "verification-before-completion",
        )
        runtime_files = [
            ROOT / "SKILL.md",
            ROOT / "README.md",
            ROOT / "README_EN.md",
            *sorted((ROOT / "references").glob("*.md")),
            *sorted((ROOT / "scripts").glob("*.py")),
        ]
        for path in runtime_files:
            text = path.read_text(encoding="utf-8").lower()
            for skill_name in forbidden:
                self.assertNotIn(skill_name, text, f"cross-skill dependency in {path.relative_to(ROOT)}")

        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("stable requirement IDs with acceptance signals", skill)
        self.assertIn("run fresh scope-appropriate checks after the latest write", skill)

    def test_local_paths_are_generic(self):
        local_path = re.compile(
            r"(?i)(?:[a-z]:\\(?!path(?:\\|$))|/(?:home|users|var|srv|workspace)(?:/|$))"
        )
        tracked = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout.decode("utf-8").split("\0")
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard", "-z"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout.decode("utf-8").split("\0")
        for relative in sorted(set(tracked + untracked) - {""}):
            path = ROOT / relative
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".md", ".json", ".jsonl", ".yaml", ".yml", ".py"}:
                continue
            text = path.read_text(encoding="utf-8")
            self.assertIsNone(local_path.search(text), f"local path remains in {path.relative_to(ROOT)}")


if __name__ == "__main__":
    unittest.main()
