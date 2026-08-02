# 执行与结果判定

## 建议顺序

1. 开发中：执行当前业务板块及依赖的专项验证。
2. 完工前：最后一次文件写入后，由代理无需用户提醒自动执行项目声明的权威完工入口；验证后如又写入任一范围内文件必须重跑。项目未声明入口时执行 `changed + completion`，覆盖未提交、暂存、未跟踪和需要时的分支差异。
3. 高影响或框架变更：执行 `all + full`。
4. 发布前：执行 `all + release`，并按项目规则补 runtime、migration、real-device 或 post-release 证据。

标准 JSON 布局可使用：

```powershell
python scripts/regression_verification.py audit --root D:\path\to\project
python scripts/regression_verification.py run --root D:\path\to\project --changed --profile completion --execute
python scripts/regression_verification.py run --root D:\path\to\project --all --profile full --execute
```

不带 `--execute` 时只输出经过校验的命令参数，不运行项目代码。

## 状态语义

| 状态 | 含义 | 可以宣称完成 |
| --- | --- | --- |
| `PASS` | 检查真实执行并通过 | 是 |
| `FAIL` | 产品、契约、测试、构建或清理失败 | 否 |
| `BLOCKED` | 环境、前置条件、授权或外部证据缺失 | 否 |
| `KNOWN_FAIL` | 与未过期的精确失败指纹一致 | 否 |
| `SKIPPED` | 仅展示或未执行 | 否 |

只要有效要求仍为 `FAIL`、`BLOCKED`、`KNOWN_FAIL`、`SKIPPED`、部分完成或未验证，就不得报告任务完成、可提交、可发布或无遗漏。

## 失败归因

先判断失败属于当前改动、现有基线、并发环境、平台差异、缺少依赖还是外部证据。基线噪音也必须保留真实状态；可以同时给出专项通过证据，但不得把专项通过描述为完整门禁通过。

环境阻塞需要记录缺失的命令、服务、设备、权限或证据，以及解除阻塞后应执行的准确入口。不要通过跳过检查、扩大已知失败、删除断言或伪造空报告来获得绿色结果。

## 完工证据

最终报告至少包含：

- 本次需求台账与变更仓库；
- 选择的板块和依赖扩展原因；
- 执行的配置档、检查数量、状态和退出码；
- 结构化报告路径与新鲜执行时间；
- 任何未执行的风险档及原因；
- 数据、缓存、队列和临时文件恢复证据；
- 差异复核、提交和推送结果。
