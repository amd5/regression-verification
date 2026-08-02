import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "regression_verification.py"
SPEC = importlib.util.spec_from_file_location("regression_verification", SCRIPT_PATH)
regression_verification = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = regression_verification
SPEC.loader.exec_module(regression_verification)


class RegressionVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.regression = self.root / "regression"
        (self.regression / "modules" / "core").mkdir(parents=True)
        (self.regression / "profiles").mkdir()
        (self.regression / "run.py").write_text("print('PASS')\n", encoding="utf-8")
        self.write_json(
            "catalog.json",
            {
                "schema_version": 1,
                "default_profile": "completion",
                "repositories": {"backend": {"title": "后端", "path": ".", "default_branch": "main"}},
                "profiles": {"completion": "profiles/completion.json"},
                "modules": ["modules/core/module.json"],
            },
        )
        self.write_json(
            "profiles/completion.json",
            {
                "name": "completion",
                "title": "完工检查",
                "tiers": ["quick"],
                "allowed_risks": ["read_only"],
            },
        )
        self.write_json(
            "checks.json",
            {
                "schema_version": 1,
                "checks": [
                    {
                        "id": "backend.tests",
                        "title": "后端测试",
                        "repo": "backend",
                        "kind": "command",
                        "command": ["python", "-m", "unittest"],
                        "tier": "quick",
                        "risk": "read_only",
                        "timeout_seconds": 60,
                    }
                ],
            },
        )
        self.write_json(
            "modules/core/module.json",
            {
                "id": "core",
                "title": "核心",
                "description": "核心回归",
                "depends_on": [],
                "triggers": {"backend": ["src/**"]},
                "check_ids": ["backend.tests"],
            },
        )
        self.write_json(
            "native_test_inventory.json",
            {
                "schema_version": 1,
                "suites": [
                    {
                        "id": "backend.unit",
                        "repo": "backend",
                        "check_id": "backend.tests",
                        "include": ["tests/test_*.py"],
                    }
                ],
            },
        )
        self.write_json("known_failures.json", [])

    def tearDown(self):
        self.temporary_directory.cleanup()

    def write_json(self, relative, value):
        path = self.regression / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def read_json(self, relative):
        return json.loads((self.regression / relative).read_text(encoding="utf-8"))

    def enable_ui_inventory(self):
        catalog = self.read_json("catalog.json")
        catalog["modules"].append("modules/ui-design/module.json")
        self.write_json("catalog.json", catalog)
        self.write_json(
            "modules/ui-design/module.json",
            {
                "id": "ui-design",
                "title": "UI 与设计图",
                "description": "界面回归",
                "depends_on": ["core"],
                "triggers": {"backend": ["ui/**"]},
                "check_ids": ["backend.tests"],
            },
        )
        self.write_json(
            "ui_design_inventory.json",
            {
                "schema_version": 1,
                "title": "UI 清单",
                "repositories": {
                    "backend": {"applicability": "ui", "candidate_patterns": ["ui/**"]}
                },
                "surfaces": [
                    {
                        "id": "backend.ui",
                        "title": "后端界面",
                        "repo": "backend",
                        "platform": "web",
                        "implementation_patterns": ["ui/**"],
                        "design_sources": [
                            {
                                "kind": "implementation-contract",
                                "status": "not_provided",
                                "reason": "没有批准设计图",
                                "authority": "运行态证据",
                            }
                        ],
                        "states": ["默认"],
                        "viewports": [{"label": "桌面", "width": 1280, "height": 800}],
                        "check_ids": ["backend.tests"],
                        "evidence_profiles": ["completion"],
                        "comparison": {"mode": "screenshot", "checks": ["无空白"]},
                    }
                ],
            },
        )

    def enable_codex_rework_inventory(self):
        checks = self.read_json("checks.json")
        checks["checks"].append({
            "id": "backend.rework-audit", "title": "返工审计", "repo": "backend",
            "kind": "command", "command": ["python", "audit.py"], "tier": "quick",
            "risk": "read_only", "timeout_seconds": 60,
        })
        self.write_json("checks.json", checks)
        catalog = self.read_json("catalog.json")
        catalog["modules"].append("modules/codex-rework/module.json")
        self.write_json("catalog.json", catalog)
        self.write_json("modules/codex-rework/module.json", {
            "id": "codex-rework", "title": "重复返工", "description": "重复返工门禁",
            "always": True, "depends_on": ["core"], "triggers": {},
            "check_ids": ["backend.tests", "backend.rework-audit"],
        })
        self.write_json("codex_rework_inventory.json", {
            "schema_version": 1, "parser_version": 1, "promotion_threshold": 3,
            "privacy": "不保存原文", "scan": {}, "promoted_check_ids": ["backend.tests"],
            "promotions": [{
                "id": "0123456789abcdef", "entity_type": "path", "repo": "backend",
                "path": "src/a.py", "cycle_count": 3, "first_cycle_at": "2026-01-01T00:00:00Z",
                "last_cycle_at": "2026-01-03T00:00:00Z", "evidence_hashes": ["1111111111111111"],
                "check_ids": ["backend.tests"],
            }],
        })

    def test_valid_center_passes_audit(self):
        result = regression_verification.audit_project(self.root)
        self.assertEqual(result.status, "PASS", result.errors)
        self.assertEqual(result.modules, 1)
        self.assertEqual(result.checks, 1)
        self.assertEqual(result.inventory_suites, 1)
        self.assertEqual(result.ui_surfaces, 0)

    def test_optional_ui_design_inventory_passes_and_is_counted(self):
        self.enable_ui_inventory()

        result = regression_verification.audit_project(self.root)

        self.assertEqual(result.status, "PASS", result.errors)
        self.assertEqual(result.ui_surfaces, 1)

    def test_optional_codex_rework_inventory_passes_and_is_counted(self):
        self.enable_codex_rework_inventory()

        result = regression_verification.audit_project(self.root)

        self.assertEqual(result.status, "PASS", result.errors)
        self.assertEqual(result.codex_rework_promotions, 1)

    def test_rejects_codex_rework_privacy_leak_and_short_cycle(self):
        self.enable_codex_rework_inventory()
        inventory = self.read_json("codex_rework_inventory.json")
        inventory["promotions"][0]["cycle_count"] = 2
        inventory["promotions"][0]["user_message"] = "不要保存"
        self.write_json("codex_rework_inventory.json", inventory)

        result = regression_verification.audit_project(self.root)

        self.assertIn("Codex 重复返工循环不足 3 次：0123456789abcdef", result.errors)
        self.assertIn("Codex 重复返工清单包含禁止原文字段：user_message", result.errors)

    def test_rejects_ui_design_unknown_check_and_module_drift(self):
        self.enable_ui_inventory()
        inventory = self.read_json("ui_design_inventory.json")
        inventory["surfaces"][0]["check_ids"] = ["missing.ui-check"]
        self.write_json("ui_design_inventory.json", inventory)

        result = regression_verification.audit_project(self.root)

        self.assertIn("UI 界面表面引用未知检查：backend.ui -> missing.ui-check", result.errors)
        self.assertIn("ui-design 模块检查与 UI 界面表面检查不一致", result.errors)

    def test_rejects_shell_string_and_unreferenced_check(self):
        document = self.read_json("checks.json")
        document["checks"][0]["command"] = "python -m unittest"
        document["checks"].append(
            {
                "id": "backend.orphan",
                "title": "遗漏检查",
                "repo": "backend",
                "kind": "instruction",
                "instruction": "需要外部证据",
                "tier": "runtime",
                "risk": "local_runtime",
            }
        )
        self.write_json("checks.json", document)

        result = regression_verification.audit_project(self.root)

        self.assertEqual(result.status, "FAIL")
        self.assertTrue(any("参数数组" in error for error in result.errors))
        self.assertIn("检查未被任何模块引用：backend.orphan", result.errors)

    def test_rejects_dependency_cycle_and_unknown_check(self):
        catalog = self.read_json("catalog.json")
        catalog["modules"].append("modules/other/module.json")
        self.write_json("catalog.json", catalog)
        core = self.read_json("modules/core/module.json")
        core["depends_on"] = ["other"]
        self.write_json("modules/core/module.json", core)
        self.write_json(
            "modules/other/module.json",
            {
                "id": "other",
                "title": "其他",
                "description": "其他回归",
                "depends_on": ["core"],
                "triggers": {"backend": ["docs/**"]},
                "check_ids": ["missing.check"],
            },
        )

        result = regression_verification.audit_project(self.root)

        self.assertTrue(any("循环" in error for error in result.errors))
        self.assertIn("模块引用未知检查：other -> missing.check", result.errors)

    def test_rejects_manifest_path_escape(self):
        catalog = self.read_json("catalog.json")
        catalog["modules"] = ["../outside.json"]
        self.write_json("catalog.json", catalog)

        result = regression_verification.audit_project(self.root)

        self.assertTrue(any("越出 regression" in error for error in result.errors))

    def test_rejects_expired_known_failure(self):
        self.write_json(
            "known_failures.json",
            [
                {
                    "check_id": "backend.tests",
                    "fingerprint": "sha256:example",
                    "reason": "等待修复",
                    "owner": "team",
                    "expires_on": (date.today() - timedelta(days=1)).isoformat(),
                }
            ],
        )

        result = regression_verification.audit_project(self.root)

        self.assertTrue(any("已经过期" in error for error in result.errors))

    def test_rejects_invalid_native_inventory_exclude(self):
        inventory = self.read_json("native_test_inventory.json")
        inventory["suites"][0]["exclude"] = "tests/slow/**"
        self.write_json("native_test_inventory.json", inventory)

        result = regression_verification.audit_project(self.root)

        self.assertIn("原生验证 exclude 必须是字符串数组：backend.unit", result.errors)

    def test_builds_changed_command_with_default_profile_and_base(self):
        command = regression_verification.build_run_command(
            self.root,
            mode="changed",
            profile=None,
            base="default",
        )

        self.assertEqual(command[-5:], ["--changed", "--profile", "completion", "--base", "default"])

    def test_builds_repeated_module_arguments(self):
        command = regression_verification.build_run_command(
            self.root,
            mode="module",
            profile="completion",
            modules=["core", "core"],
        )

        self.assertEqual(command[-6:], ["--module", "core", "--module", "core", "--profile", "completion"])

    def test_rejects_unknown_profile_or_module(self):
        with self.assertRaises(regression_verification.VerificationError):
            regression_verification.build_run_command(self.root, mode="all", profile="release")
        with self.assertRaises(regression_verification.VerificationError):
            regression_verification.build_run_command(
                self.root,
                mode="module",
                profile="completion",
                modules=["missing"],
            )


if __name__ == "__main__":
    unittest.main()
