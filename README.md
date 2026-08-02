# regression-verification

当前版本：`2.0.6`

项目仓库：<https://github.com/amd5/regression-verification>

## 简介

`regression-verification` 是一个面向 Codex、Claude Code、Agent Skills 和其他智能编码代理的回归验证技能。它用于建立、维护、审计和执行一个或多个相关仓库的模块化回归门禁，确保代理在最后一次文件写入后自动执行项目声明的权威完工入口，无需用户提醒；验证后如又写入文件则重新执行，并保留可复核证据。

技能按业务板块组织验证，不按仓库堆叠命令。各语言和平台的原生测试继续留在所属仓库；统一回归中心只负责发现、选择、补齐依赖、执行、分类结果和保存脱敏报告。

## 核心能力

- 识别已有 `regression/` 中心并优先沿用项目契约；
- 维护仓库、板块、触发路径、依赖、检查、配置档和原生测试清单；
- 根据工作区、暂存区、未跟踪文件和可选默认分支差异选择板块；
- 把单体检查器按稳定检查 ID 拆分映射到业务板块；
- 全量审计 `tools/`、脚本和各仓原生验证入口，阻止漏登记、重复和空套件；
- 审计 UI 表面、批准设计源、状态、视口、截图证据、组件、样式和视觉运行态，阻止界面候选漏登记或伪通过；
- 在用户明确授权时全量扫描 Codex 历史，把同一文件、具体模块或真实 UI 表面至少 3 次完整“写入、人工要求还原、再次写入”循环自动晋升为脱敏常驻回归项；
- 区分 completion、full、release、runtime、migration、real-device 和 post-release；
- 保留 `PASS`、`FAIL`、`BLOCKED`、`KNOWN_FAIL` 和 `SKIPPED` 的真实语义；
- 强制数据库、Redis、队列和临时文件隔离、恢复与零残留证据。

## 适用场景

- 每次开发、修复或重构完成前执行防回归验证；
- 多端、多仓接口与配置联动检查；
- 新增接口、字段、状态、协议、命令、脚本或工具后补回归覆盖；
- 把庞大的契约检查器拆分为可按板块选择的检查；
- 审计历史验证入口、Codex 会话中暴露的缺口或遗漏检查；
- 自动识别 Codex 误改后被用户反复要求还原的程序或 UI，并把稳定检查加入长期回归；
- 为 UI、布局、组件、样式、设计图或截图变化建立自动化、运行态和真机分层门禁；
- 发布前执行完整构建、运行态、真机和生产回读门禁。

普通解释、状态询问、明确禁止验证的请求，以及无项目改动的一次性讨论不应触发本技能。

## 标准工作流

1. 登记需求和项目规则，确定相关仓库与风险边界。
2. 发现现有测试、工具、脚本、文档检查和回归中心。
3. 按业务板块映射触发路径、跨板块依赖和检查 ID。
4. 审计目录结构、引用、命令数组、清单和已知失败有效期。
5. UI/设计变更额外核对设计源、状态、视口和证据档；授权 Codex 历史时全量识别至少 3 次的完整返工循环并审计脱敏清单。
6. 开发中执行专项板块；最后一次文件写入后自动执行项目声明的权威完工入口，验证后如又写入则重跑。项目未声明入口时执行 changed + completion；高影响或回归框架变更执行 full。
7. 发布任务执行 release 和需要的外部证据档；使用新鲜结果逐项关闭需求，任何阻塞或已知失败都不冒充通过。

## 确定性工具

审计标准 JSON 回归目录：

```powershell
python scripts/regression_verification.py audit --root D:\path\to\project
```

只生成经过校验的 changed 命令：

```powershell
python scripts/regression_verification.py run --root D:\path\to\project --changed --profile completion
```

实际执行：

```powershell
python scripts/regression_verification.py run --root D:\path\to\project --changed --profile completion --execute
```

专项与全量：

```powershell
python scripts/regression_verification.py run --root D:\path\to\project --module api-contract --profile completion --execute
python scripts/regression_verification.py run --root D:\path\to\project --all --profile full --execute
```

工具只识别项目根目录内的 `regression/run.php`、`run.py`、`run.ps1` 或 `run.sh`，不会执行清单中的任意 shell 字符串。执行前必须通过结构审计；项目自己的 runner 和框架自测仍是运行行为的权威来源。

## 安全边界

- 不复制或重写原仓测试实现；
- 不隐式扫描私人 Codex 会话；只有用户明确授权时才全量扫描指定范围；
- 不把项目规则注入、技术 rollback、业务恢复、只有两次的返工，或测试/工具/资源分类误计为真实 UI 循环；不提交会话正文、命令原文、凭证或完整会话/任务 ID；
- 不自动执行生产写入、迁移、节点控制、凭据操作或真机验收；
- 不把缺少环境、依赖、授权或外部证据报告为成功；
- 不用构建或组件测试替代必需的浏览器、原始设计图、截图、交互或真机证据，也不从截图反推有权威标注的布局参数；
- 不以扩大已知失败、删除断言或跳过套件换取绿色结果；
- 不提交项目回归报告、密钥、环境文件或目标业务仓库内容到技能仓库。

## 安装

PowerShell：

```powershell
$skillsRoot = Join-Path $env:USERPROFILE ".codex\skills"
git clone https://github.com/amd5/regression-verification.git (Join-Path $skillsRoot "regression-verification")
```

Bash：

```bash
git clone https://github.com/amd5/regression-verification.git \
  "$CODEX_HOME/skills/regression-verification"
```

示例调用：

```text
使用 $regression-verification，审计多个关联仓库当前变更的回归覆盖，并执行完工门禁。
```

## 技能维护与发布

任何技能包修改都必须完成测试、版本递增、提交、`main` 与标签原子推送，以及 GitHub Release 回读：

```powershell
python scripts/release_skill.py --message "描述本次技能更新"
```

不兼容迁移使用 `--bump major`。完整规则见 `references/release-workflow.md`。

## 目录

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

## 许可证

本项目使用仓库内 `LICENSE` 指定的许可证。
