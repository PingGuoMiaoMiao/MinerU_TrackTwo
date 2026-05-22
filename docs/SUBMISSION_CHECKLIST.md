# 提交自检清单

## 1. 代码与开源仓库

- [ ] 创建 GitHub 仓库并推送项目代码。
- [ ] 仓库包含 `src/`、`docs/`、`samples/`、`scripts/`、`requirements.txt`、`README.md`、`.env.example`。
- [ ] 仓库不包含 `.env`、API Key、`data/` 运行数据、`.mineru-py312/` 本地环境、`local_mineru_output/` 大型中间产物。
- [ ] README 中的启动命令已验证：`python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload`。
- [ ] 最小烟测通过：`python scripts/run_smoke_tests.py`。

## 2. 部署与接口说明

- [ ] 明确运行环境：Python 3.12/3.13、Windows 或 Linux、依赖安装命令。
- [ ] 明确 `.env` 配置：LLM、DeepSeek、MinerU SaaS、本地 MinerU CLI。
- [ ] 提供 API 说明：[API.md](API.md)。
- [ ] 提供可访问服务地址，或提供本地复现命令。
- [ ] 说明日志查看方式：`GET /v1/tasks/{task_id}/logs`。

## 3. 技术报告

- [ ] 技术报告包含整体架构、任务规划机制、工具调用、MinerU 接入、异常恢复和稳定性设计。
- [ ] 技术报告包含不少于 5 个典型任务示例。
- [ ] 技术报告说明适用场景、产业价值和后续增强方向。

## 4. 测试材料

- [ ] 本地样例测试结果保留：`test_files_en/test_results.json`。
- [ ] 公开 PDF 测试结果保留：`web_pdfs/web_pdf_test_results.json`。
- [ ] 测试报告说明样例类型、状态、解析器和输出摘要：[TEST_REPORT.md](TEST_REPORT.md)。
- [ ] 至少保留一条成功任务日志，用于展示任务输入、计划、工具调用、输出和质量检查。

## 5. 演示材料

- [ ] 准备 5-8 页 PPT：痛点、方案、架构、MinerU 工具链、任务演示、测试结果、价值。
- [ ] 准备 3 分钟演示脚本：[DEMO_SCRIPT.md](DEMO_SCRIPT.md)。
- [ ] 演示时展示 API 文档、任务提交、结果查询和日志查询。
- [ ] 演示前确认本机或服务器上的 `.env` 已配置可用 LLM 与 MinerU Key。

## 6. 推荐提交包

```text
README.md
requirements.txt
.env.example
src/
docs/
samples/
scripts/
test_files_en/test_results.json
web_pdfs/web_pdf_test_results.json
```

如提交平台允许补充材料，可额外上传 PPT、演示视频和公开服务地址。
