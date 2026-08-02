#!/usr/bin/env python3
"""Audit and safely invoke a project-owned modular regression center."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any


ALLOWED_CHECK_KINDS = {"command", "instruction", "git_path_absent", "git_content_absent"}
ID_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789-.")


class VerificationError(RuntimeError):
    pass


@dataclass
class AuditResult:
    root: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    repositories: int = 0
    profiles: int = 0
    modules: int = 0
    checks: int = 0
    inventory_suites: int = 0
    ui_surfaces: int = 0
    codex_rework_promotions: int = 0

    @property
    def status(self) -> str:
        return "PASS" if not self.errors else "FAIL"

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "root": str(self.root),
            "counts": {
                "repositories": self.repositories,
                "profiles": self.profiles,
                "modules": self.modules,
                "checks": self.checks,
                "inventory_suites": self.inventory_suites,
                "ui_surfaces": self.ui_surfaces,
                "codex_rework_promotions": self.codex_rework_promotions,
            },
            "errors": self.errors,
            "warnings": self.warnings,
        }


def valid_id(value: object, *, allow_dot: bool = False) -> bool:
    if not isinstance(value, str) or not value or not value[0].islower():
        return False
    allowed = ID_CHARS if allow_dot else ID_CHARS - {"."}
    return all(character in allowed for character in value)


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def read_json(path: Path, result: AuditResult, label: str, default: Any) -> Any:
    if not path.is_file():
        result.errors.append(f"缺少{label}：{path}")
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        result.errors.append(f"{label}不是有效 UTF-8 JSON：{path}：{exc}")
        return default


def resolve_manifest(regression: Path, relative: object, result: AuditResult, label: str) -> Path | None:
    if not isinstance(relative, str) or not relative:
        result.errors.append(f"{label}路径必须是非空字符串")
        return None
    path = (regression / relative).resolve()
    if not is_within(path, regression):
        result.errors.append(f"{label}路径越出 regression 目录：{relative}")
        return None
    return path


def validate_command(check: dict[str, Any], result: AuditResult, check_id: str) -> None:
    command = check.get("command")
    platform_commands = check.get("command_by_platform")
    if command is None and platform_commands is None:
        result.errors.append(f"命令检查缺少 command 或 command_by_platform：{check_id}")
        return
    commands: list[tuple[str, object]] = []
    if command is not None:
        commands.append(("command", command))
    if platform_commands is not None:
        if not isinstance(platform_commands, dict) or not platform_commands:
            result.errors.append(f"command_by_platform 必须是非空对象：{check_id}")
        else:
            commands.extend((f"command_by_platform.{key}", value) for key, value in platform_commands.items())
    for label, value in commands:
        if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
            result.errors.append(f"{label} 必须是非空参数数组，禁止 shell 字符串：{check_id}")
    timeout = check.get("timeout_seconds")
    if not isinstance(timeout, int) or timeout <= 0:
        result.errors.append(f"命令检查必须声明正数 timeout_seconds：{check_id}")


def detect_cycles(dependencies: dict[str, list[str]], result: AuditResult) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(module_id: str, trail: list[str]) -> None:
        if module_id in visiting:
            start = trail.index(module_id)
            result.errors.append("模块依赖存在循环：" + " -> ".join(trail[start:] + [module_id]))
            return
        if module_id in visited:
            return
        visiting.add(module_id)
        for dependency in dependencies.get(module_id, []):
            visit(dependency, trail + [module_id])
        visiting.remove(module_id)
        visited.add(module_id)

    for module_id in dependencies:
        visit(module_id, [])


def audit_ui_design_inventory(
    regression: Path,
    repositories: dict[str, Any],
    profiles: set[str],
    checks: dict[str, dict[str, Any]],
    modules: dict[str, dict[str, Any]],
    result: AuditResult,
) -> None:
    path = regression / "ui_design_inventory.json"
    if not path.exists():
        return
    inventory = read_json(path, result, "UI 与设计图清单", {})
    if not isinstance(inventory, dict):
        result.errors.append("ui_design_inventory.json 顶层必须是对象")
        return
    if inventory.get("schema_version") != 1:
        result.errors.append("ui_design_inventory.schema_version 必须为 1")
    configured_repositories = inventory.get("repositories")
    if not isinstance(configured_repositories, dict) or set(configured_repositories) != set(repositories):
        result.errors.append("UI 与设计图清单必须完整覆盖 catalog.repositories")

    raw_surfaces = inventory.get("surfaces")
    if not isinstance(raw_surfaces, list) or not raw_surfaces:
        result.errors.append("ui_design_inventory.surfaces 必须是非空数组")
        return
    surface_ids: set[str] = set()
    surface_checks: set[str] = set()
    for index, surface in enumerate(raw_surfaces):
        if not isinstance(surface, dict):
            result.errors.append(f"UI 界面表面必须是对象：索引 {index}")
            continue
        surface_id = surface.get("id")
        if not valid_id(surface_id, allow_dot=True) or surface_id in surface_ids:
            result.errors.append(f"UI 界面表面 ID 无效或重复：{surface_id}")
        else:
            surface_ids.add(surface_id)
        if surface.get("repo") not in repositories:
            result.errors.append(f"UI 界面表面引用未知仓库：{surface_id} -> {surface.get('repo')}")
        for key in ("implementation_patterns", "states", "check_ids", "evidence_profiles"):
            values = surface.get(key)
            if not isinstance(values, list) or not values or not all(isinstance(item, str) and item for item in values):
                result.errors.append(f"UI 界面表面 {surface_id} 的 {key} 必须是非空字符串数组")
        for check_id in surface.get("check_ids", []) if isinstance(surface.get("check_ids"), list) else []:
            if check_id not in checks:
                result.errors.append(f"UI 界面表面引用未知检查：{surface_id} -> {check_id}")
            surface_checks.add(str(check_id))
        for profile_id in surface.get("evidence_profiles", []) if isinstance(surface.get("evidence_profiles"), list) else []:
            if profile_id not in profiles:
                result.errors.append(f"UI 界面表面引用未知配置档：{surface_id} -> {profile_id}")
        design_sources = surface.get("design_sources")
        if not isinstance(design_sources, list) or not design_sources:
            result.errors.append(f"UI 界面表面缺少设计源或未提供原因：{surface_id}")
        viewports = surface.get("viewports")
        if not isinstance(viewports, list) or not viewports:
            result.errors.append(f"UI 界面表面缺少视口：{surface_id}")
        comparison = surface.get("comparison")
        if not isinstance(comparison, dict) or comparison.get("mode") not in {
            "structural",
            "annotation",
            "screenshot",
            "manual-overlay",
        }:
            result.errors.append(f"UI 界面表面比较方式无效：{surface_id}")

    ui_module = modules.get("ui-design")
    if not isinstance(ui_module, dict):
        result.errors.append("存在 UI 与设计图清单但缺少 ui-design 业务板块")
    else:
        module_checks = {str(value) for value in ui_module.get("check_ids", [])}
        if module_checks != surface_checks:
            result.errors.append("ui-design 模块检查与 UI 界面表面检查不一致")
    result.ui_surfaces = len(surface_ids)


def audit_codex_rework_inventory(
    regression: Path,
    checks: dict[str, dict[str, Any]],
    modules: dict[str, dict[str, Any]],
    result: AuditResult,
) -> None:
    path = regression / "codex_rework_inventory.json"
    if not path.exists():
        return
    inventory = read_json(path, result, "Codex 重复返工清单", {})
    if not isinstance(inventory, dict):
        result.errors.append("codex_rework_inventory.json 顶层必须是对象")
        return
    if inventory.get("schema_version") != 1:
        result.errors.append("Codex 重复返工清单 schema_version 必须为 1")
    if inventory.get("promotion_threshold") != 3:
        result.errors.append("Codex 重复返工晋升阈值必须为 3")
    promotions = inventory.get("promotions")
    if not isinstance(promotions, list):
        result.errors.append("Codex 重复返工 promotions 必须是数组")
        promotions = []
    promotion_ids: set[str] = set()
    promotion_checks: set[str] = set()
    forbidden_keys = {"user_message", "command_text", "session_id", "task_id", "conversation_text"}

    def inspect_keys(value: Any) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                if str(key).lower() in forbidden_keys:
                    result.errors.append(f"Codex 重复返工清单包含禁止原文字段：{key}")
                inspect_keys(nested)
        elif isinstance(value, list):
            for nested in value:
                inspect_keys(nested)

    inspect_keys(inventory)
    for index, promotion in enumerate(promotions):
        if not isinstance(promotion, dict):
            result.errors.append(f"Codex 重复返工晋升项必须是对象：索引 {index}")
            continue
        promotion_id = promotion.get("id")
        if not isinstance(promotion_id, str) or re.fullmatch(r"[a-f0-9]{16}", promotion_id) is None or promotion_id in promotion_ids:
            result.errors.append(f"Codex 重复返工晋升 ID 无效或重复：{promotion_id}")
        else:
            promotion_ids.add(promotion_id)
        if promotion.get("entity_type") not in {"path", "module", "ui_surface"}:
            result.errors.append(f"Codex 重复返工实体类型无效：{promotion_id}")
        if not isinstance(promotion.get("cycle_count"), int) or promotion.get("cycle_count", 0) < 3:
            result.errors.append(f"Codex 重复返工循环不足 3 次：{promotion_id}")
        hashes = promotion.get("evidence_hashes")
        if not isinstance(hashes, list) or len(hashes) > 3 or any(not isinstance(value, str) or re.fullmatch(r"[a-f0-9]{16}", value) is None for value in hashes):
            result.errors.append(f"Codex 重复返工截断哈希无效：{promotion_id}")
        check_ids = promotion.get("check_ids")
        if not isinstance(check_ids, list) or not check_ids:
            result.errors.append(f"Codex 重复返工晋升项缺少稳定检查：{promotion_id}")
            check_ids = []
        for check_id in check_ids:
            if check_id not in checks:
                result.errors.append(f"Codex 重复返工引用未知检查：{promotion_id} -> {check_id}")
            promotion_checks.add(str(check_id))
    declared_checks = inventory.get("promoted_check_ids")
    if not isinstance(declared_checks, list) or set(map(str, declared_checks)) != promotion_checks:
        result.errors.append("Codex 重复返工 promoted_check_ids 与晋升项不一致")
    module = modules.get("codex-rework")
    if not isinstance(module, dict) or module.get("always") is not True:
        result.errors.append("存在 Codex 重复返工清单但缺少 always=true 的 codex-rework 板块")
    elif not promotion_checks.issubset(set(map(str, module.get("check_ids", [])))):
        result.errors.append("codex-rework 板块没有包含全部晋升检查")
    result.codex_rework_promotions = len(promotion_ids)


def audit_project(root: Path) -> AuditResult:
    root = root.resolve()
    result = AuditResult(root=root)
    regression = root / "regression"
    if not regression.is_dir():
        result.errors.append(f"缺少 regression 目录：{regression}")
        return result

    catalog = read_json(regression / "catalog.json", result, "回归目录", {})
    if not isinstance(catalog, dict):
        result.errors.append("catalog.json 顶层必须是对象")
        return result

    repositories = catalog.get("repositories")
    if not isinstance(repositories, dict) or not repositories:
        result.errors.append("catalog.repositories 必须是非空对象")
        repositories = {}
    for repo_id, config in repositories.items():
        if not valid_id(repo_id) or not isinstance(config, dict):
            result.errors.append(f"仓库定义无效：{repo_id}")
            continue
        repo_path = config.get("path")
        if not isinstance(repo_path, str) or not repo_path:
            result.errors.append(f"仓库缺少 path：{repo_id}")
        elif not (root / repo_path).resolve().is_dir():
            result.errors.append(f"仓库路径不存在：{repo_id} -> {repo_path}")
    result.repositories = len(repositories)

    profiles = catalog.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        result.errors.append("catalog.profiles 必须是非空对象")
        profiles = {}
    profile_ids: set[str] = set()
    for profile_id, relative in profiles.items():
        if not valid_id(profile_id):
            result.errors.append(f"配置档 ID 无效：{profile_id}")
            continue
        profile_path = resolve_manifest(regression, relative, result, f"配置档 {profile_id}")
        if profile_path is None:
            continue
        profile = read_json(profile_path, result, f"配置档 {profile_id}", {})
        if not isinstance(profile, dict) or profile.get("name") != profile_id:
            result.errors.append(f"配置档名称不匹配：{profile_id}")
            continue
        for key in ("tiers", "allowed_risks"):
            values = profile.get(key)
            if not isinstance(values, list) or not values or not all(isinstance(item, str) and item for item in values):
                result.errors.append(f"配置档 {profile_id} 的 {key} 必须是非空字符串数组")
        profile_ids.add(profile_id)
    default_profile = catalog.get("default_profile")
    if default_profile not in profile_ids:
        result.errors.append(f"默认配置档不存在：{default_profile}")
    result.profiles = len(profile_ids)

    checks_document = read_json(regression / "checks.json", result, "检查清单", {})
    raw_checks = checks_document.get("checks", []) if isinstance(checks_document, dict) else []
    if not isinstance(raw_checks, list) or not raw_checks:
        result.errors.append("checks.json 的 checks 必须是非空数组")
        raw_checks = []
    checks: dict[str, dict[str, Any]] = {}
    for index, check in enumerate(raw_checks):
        if not isinstance(check, dict):
            result.errors.append(f"检查项必须是对象：索引 {index}")
            continue
        check_id = check.get("id")
        if not valid_id(check_id, allow_dot=True):
            result.errors.append(f"检查 ID 无效：{check_id}")
            continue
        if check_id in checks:
            result.errors.append(f"检查 ID 重复：{check_id}")
            continue
        checks[check_id] = check
        if check.get("repo") not in repositories:
            result.errors.append(f"检查引用未知仓库：{check_id} -> {check.get('repo')}")
        kind = check.get("kind")
        if kind not in ALLOWED_CHECK_KINDS:
            result.errors.append(f"检查类型无效：{check_id} -> {kind}")
        if not isinstance(check.get("tier"), str) or not check.get("tier"):
            result.errors.append(f"检查缺少 tier：{check_id}")
        if not isinstance(check.get("risk"), str) or not check.get("risk"):
            result.errors.append(f"检查缺少 risk：{check_id}")
        if kind == "command":
            validate_command(check, result, check_id)
        if kind == "instruction" and not isinstance(check.get("instruction"), str):
            result.errors.append(f"证据检查缺少 instruction：{check_id}")
    result.checks = len(checks)

    raw_module_paths = catalog.get("modules")
    if not isinstance(raw_module_paths, list) or not raw_module_paths:
        result.errors.append("catalog.modules 必须是非空数组")
        raw_module_paths = []
    modules: dict[str, dict[str, Any]] = {}
    referenced_checks: set[str] = set()
    dependencies: dict[str, list[str]] = {}
    for index, relative in enumerate(raw_module_paths):
        module_path = resolve_manifest(regression, relative, result, f"模块索引 {index}")
        if module_path is None:
            continue
        module = read_json(module_path, result, f"模块 {relative}", {})
        module_id = module.get("id") if isinstance(module, dict) else None
        if not valid_id(module_id):
            result.errors.append(f"模块 ID 无效：{module_id}")
            continue
        if module_id in modules:
            result.errors.append(f"模块 ID 重复：{module_id}")
            continue
        modules[module_id] = module
        check_ids = module.get("check_ids")
        if not isinstance(check_ids, list) or not check_ids:
            result.errors.append(f"模块必须至少引用一项检查：{module_id}")
            check_ids = []
        if len(check_ids) != len(set(check_ids)):
            result.errors.append(f"模块检查 ID 重复：{module_id}")
        for check_id in check_ids:
            if check_id not in checks:
                result.errors.append(f"模块引用未知检查：{module_id} -> {check_id}")
            referenced_checks.add(check_id)
        module_dependencies = module.get("depends_on")
        if not isinstance(module_dependencies, list) or not all(isinstance(item, str) for item in module_dependencies):
            result.errors.append(f"模块 depends_on 必须是字符串数组：{module_id}")
            module_dependencies = []
        dependencies[module_id] = module_dependencies
        triggers = module.get("triggers")
        if not isinstance(triggers, dict) or (not triggers and not module.get("always")):
            result.errors.append(f"模块必须声明 triggers 或 always：{module_id}")
        elif isinstance(triggers, dict):
            has_trigger_pattern = False
            for repo_id, patterns in triggers.items():
                if repo_id not in repositories:
                    result.errors.append(f"模块触发器引用未知仓库：{module_id} -> {repo_id}")
                if not isinstance(patterns, list) or not all(isinstance(item, str) and item for item in patterns):
                    result.errors.append(f"模块触发路径必须是字符串数组：{module_id} -> {repo_id}")
                elif patterns:
                    has_trigger_pattern = True
            if not has_trigger_pattern and not module.get("always"):
                result.errors.append(f"模块至少需要一个触发路径或 always：{module_id}")
    for module_id, module_dependencies in dependencies.items():
        for dependency in module_dependencies:
            if dependency not in modules:
                result.errors.append(f"模块依赖不存在：{module_id} -> {dependency}")
    detect_cycles(dependencies, result)
    for check_id in sorted(set(checks) - referenced_checks):
        result.errors.append(f"检查未被任何模块引用：{check_id}")
    result.modules = len(modules)

    inventory = read_json(regression / "native_test_inventory.json", result, "原生验证清单", {})
    suites = inventory.get("suites", []) if isinstance(inventory, dict) else []
    if not isinstance(suites, list):
        result.errors.append("native_test_inventory.suites 必须是数组")
        suites = []
    suite_ids: set[str] = set()
    for index, suite in enumerate(suites):
        if not isinstance(suite, dict):
            result.errors.append(f"原生验证条目必须是对象：索引 {index}")
            continue
        suite_id = suite.get("id")
        if not valid_id(suite_id, allow_dot=True) or suite_id in suite_ids:
            result.errors.append(f"原生验证 ID 无效或重复：{suite_id}")
        else:
            suite_ids.add(suite_id)
        if suite.get("repo") not in repositories:
            result.errors.append(f"原生验证引用未知仓库：{suite_id}")
        if suite.get("check_id") not in checks:
            result.errors.append(f"原生验证引用未知检查：{suite_id} -> {suite.get('check_id')}")
        includes = suite.get("include")
        if not isinstance(includes, list) or not includes or not all(isinstance(item, str) and item for item in includes):
            result.errors.append(f"原生验证 include 必须是非空字符串数组：{suite_id}")
        excludes = suite.get("exclude", [])
        if not isinstance(excludes, list) or not all(isinstance(item, str) and item for item in excludes):
            result.errors.append(f"原生验证 exclude 必须是字符串数组：{suite_id}")
    result.inventory_suites = len(suite_ids)

    audit_ui_design_inventory(regression, repositories, profile_ids, checks, modules, result)
    audit_codex_rework_inventory(regression, checks, modules, result)

    known_failures = read_json(regression / "known_failures.json", result, "已知失败清单", [])
    if not isinstance(known_failures, list):
        result.errors.append("known_failures.json 顶层必须是数组")
        known_failures = []
    for index, failure in enumerate(known_failures):
        if not isinstance(failure, dict):
            result.errors.append(f"已知失败必须是对象：索引 {index}")
            continue
        missing = [key for key in ("check_id", "fingerprint", "reason", "owner", "expires_on") if not failure.get(key)]
        if missing:
            result.errors.append(f"已知失败缺少字段：索引 {index} -> {', '.join(missing)}")
            continue
        if failure["check_id"] not in checks:
            result.errors.append(f"已知失败引用未知检查：{failure['check_id']}")
        try:
            expires_on = date.fromisoformat(str(failure["expires_on"]))
            if expires_on < date.today():
                result.errors.append(f"已知失败已经过期：{failure['check_id']} -> {expires_on}")
        except ValueError:
            result.errors.append(f"已知失败 expires_on 无效：{failure['check_id']}")

    try:
        detect_entrypoint(root)
    except VerificationError as exc:
        result.errors.append(str(exc))
    return result


def detect_entrypoint(root: Path) -> list[str]:
    candidates = (
        ("regression/run.php", ["php"]),
        ("regression/run.py", [sys.executable, "-B"]),
        ("regression/run.ps1", ["pwsh", "-NoProfile", "-File"]),
        ("regression/run.sh", ["bash"]),
    )
    for relative, prefix in candidates:
        path = (root / relative).resolve()
        if path.is_file():
            return [*prefix, str(path)]
    raise VerificationError("缺少受支持的回归入口：regression/run.php、run.py、run.ps1 或 run.sh")


def build_run_command(
    root: Path,
    *,
    mode: str,
    profile: str | None,
    modules: list[str] | None = None,
    base: str | None = None,
) -> list[str]:
    result = audit_project(root)
    if result.errors:
        raise VerificationError("回归中心审计失败，禁止执行：" + result.errors[0])
    catalog = json.loads((root.resolve() / "regression" / "catalog.json").read_text(encoding="utf-8"))
    selected_profile = profile or catalog["default_profile"]
    if selected_profile not in catalog["profiles"]:
        raise VerificationError(f"未知配置档：{selected_profile}")
    command = detect_entrypoint(root.resolve())
    if mode == "changed":
        command.append("--changed")
    elif mode == "all":
        command.append("--all")
    elif mode == "module":
        selected_modules = modules or []
        known_modules = {
            json.loads((root.resolve() / "regression" / relative).read_text(encoding="utf-8"))["id"]
            for relative in catalog["modules"]
        }
        if not selected_modules:
            raise VerificationError("module 模式至少需要一个 --module")
        unknown = sorted(set(selected_modules) - known_modules)
        if unknown:
            raise VerificationError("未知模块：" + "、".join(unknown))
        for module_id in selected_modules:
            command.extend(["--module", module_id])
    else:
        raise VerificationError(f"未知执行模式：{mode}")
    command.extend(["--profile", selected_profile])
    if base:
        command.extend(["--base", base])
    return command


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    audit_parser = subparsers.add_parser("audit", help="审计标准回归目录的结构与引用完整性")
    audit_parser.add_argument("--root", type=Path, required=True, help="项目根目录")

    run_parser = subparsers.add_parser("run", help="审计后构造或执行项目自有回归入口")
    run_parser.add_argument("--root", type=Path, required=True, help="项目根目录")
    mode = run_parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--changed", action="store_true", help="按变更选择业务板块")
    mode.add_argument("--all", action="store_true", help="选择全部业务板块")
    mode.add_argument("--module", action="append", help="选择指定板块，可重复")
    run_parser.add_argument("--profile", help="配置档；默认使用 catalog.default_profile")
    run_parser.add_argument("--base", help="传给项目回归入口的分支比较基线")
    run_parser.add_argument("--execute", action="store_true", help="实际执行；省略时只输出命令")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.subcommand == "audit":
            result = audit_project(args.root)
            print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
            return 0 if result.status == "PASS" else 1

        mode = "changed" if args.changed else "all" if args.all else "module"
        command = build_run_command(
            args.root,
            mode=mode,
            profile=args.profile,
            modules=args.module,
            base=args.base,
        )
        if not args.execute:
            print(json.dumps({"status": "SKIPPED", "command": command}, ensure_ascii=False, indent=2))
            return 0
        completed = subprocess.run(command, cwd=args.root.resolve(), check=False)
        return completed.returncode
    except (OSError, VerificationError, json.JSONDecodeError) as exc:
        print(f"回归验证失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
