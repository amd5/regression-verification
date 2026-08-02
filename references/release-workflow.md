# 技能自动发布流程

## 长期规则

任何对本技能仓库文件的更新都必须在同一任务完成测试、版本递增、提交、`main` 分支推送、版本标签推送和 GitHub Release 回读。仅修改本地文件不算完成。普通更新递增补丁版本；技能名称或不兼容契约变化使用主版本。

## 标准命令

```powershell
python scripts/release_skill.py --message "描述本次技能更新"
```

不兼容迁移使用：

```powershell
python scripts/release_skill.py --message "描述本次技能更新" --bump major
```

脚本会执行以下门禁：

1. 确认当前目录是技能仓库根目录、分支为 `main`，且 `origin` 指向 GitHub。
2. 检查变更文件名和内容，拒绝私钥、Token、`.env` 和证书类文件。
3. 运行技能单元测试、回归审计 CLI 帮助检查和 `git diff --check`。
4. 使用 `git pull --rebase --autostash` 同步远端，再按指定级别递增 `manifest.json` 版本并同步中英文 README。
5. 重新测试后创建提交和带注释版本标签，并使用原子推送同时更新 `main` 与标签。
6. 等待 GitHub Actions 创建 Release，并通过 GitHub API 回读对应标签。

## 恢复边界

- 测试、敏感内容检查或差异检查失败时禁止提交和推送，保留工作区供维护者修复。
- 原子推送失败时保留本地提交和标签；先处理网络、鉴权或远端差异，再重新执行发布或定向推送，禁止重写远端历史。
- 标签已推送但 Release 尚未生成时，运行 `python scripts/release_skill.py --verify-release <tag>` 回读，不重复递增版本。
- 发布脚本只提交当前独立技能仓库，不得复制目标业务项目、回归报告、凭据或私有会话。
